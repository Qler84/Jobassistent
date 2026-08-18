"""Versand von Bewerbungen per SMTP.

Zugangsdaten kommen aus dem verschluesselten Vault des Nutzers (smtp_host,
smtp_port, smtp_user, smtp_password - App-Passwort empfohlen). Wird nur
aufgerufen, wenn eine Bewerbung bereits manuell freigegeben wurde UND der
Nutzer den Auto-Versand explizit in den Einstellungen aktiviert hat
(Vorschau-Modus ist Standard, siehe settings_view.py).
"""
from __future__ import annotations

import mimetypes
import smtplib
from contextlib import contextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Iterator

_TIMEOUT = 30

_TIMEOUT_HINWEIS = (
    "Zeitueberschreitung beim Verbindungsaufbau zum SMTP-Server. Moegliche Ursachen: "
    "(1) Windows-Firewall oder Antivirus blockiert JobAssistent.exe fuer ausgehende "
    "Verbindungen - pruefe, ob beim ersten Start eine Firewall-Meldung erschienen ist und "
    "die App dort zugelassen wurde. (2) Server/Port falsch (Port 465 = SSL, jeder andere "
    "Port z.B. 587 = STARTTLS). (3) Keine oder instabile Internetverbindung."
)


class SmtpError(Exception):
    pass


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    use_ssl: bool = True


@contextmanager
def _connect(config: SmtpConfig) -> Iterator[smtplib.SMTP]:
    try:
        if config.use_ssl:
            server = smtplib.SMTP_SSL(config.host, config.port, timeout=_TIMEOUT)
        else:
            server = smtplib.SMTP(config.host, config.port, timeout=_TIMEOUT)
            server.starttls()
        server.login(config.user, config.password)
    except TimeoutError as exc:
        raise SmtpError(_TIMEOUT_HINWEIS) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise SmtpError(f"SMTP-Verbindung fehlgeschlagen: {exc}") from exc

    try:
        yield server
    except TimeoutError as exc:
        raise SmtpError(_TIMEOUT_HINWEIS) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise SmtpError(f"E-Mail-Versand fehlgeschlagen: {exc}") from exc
    finally:
        try:
            server.quit()
        except (smtplib.SMTPException, OSError):
            pass


def test_connection(config: SmtpConfig) -> None:
    """Baut nur Verbindung + Login auf (ohne zu senden) - fuer den
    'SMTP-Verbindung testen'-Button im Profil-Tab. Wirft SmtpError mit
    verstaendlicher Fehlermeldung bei Problemen."""
    with _connect(config):
        pass


def send_application_email(
    config: SmtpConfig,
    empfaenger: str,
    betreff: str,
    text: str,
    anhaenge: list[Path],
    absender_name: str = "",
) -> str:
    """Versendet eine Bewerbung per SMTP und gibt die erzeugte Message-ID
    zurueck (wird in der DB gespeichert, um spaeter per IMAP passende
    Antworten zuverlaessig zuzuordnen). `anhaenge` enthaelt ausschliesslich
    die im Profil hinterlegten Anlagen (Zeugnisse etc.) - das generierte
    Anschreiben-PDF wird nicht mitgeschickt, der Brieftext geht als
    E-Mail-Text raus."""
    # Fehlender Date-Header und eine Message-ID ohne die eigene Absender-Domain
    # sind klassische Spam-Signale - beides explizit setzen statt dem Server
    # zu ueberlassen (nicht jeder SMTP-Server ergaenzt das zuverlaessig).
    absender_domain = config.user.split("@", 1)[-1] if "@" in config.user else None

    msg = EmailMessage()
    msg["From"] = f"{absender_name} <{config.user}>" if absender_name else config.user
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    msg["Date"] = formatdate(localtime=True)
    message_id = make_msgid(domain=absender_domain)
    msg["Message-ID"] = message_id
    msg.set_content(text)

    for anhang in anhaenge:
        if not anhang.exists():
            continue
        content_type, _ = mimetypes.guess_type(anhang.name)
        maintype, _, subtype = (content_type or "application/octet-stream").partition("/")
        msg.add_attachment(
            anhang.read_bytes(),
            maintype=maintype,
            subtype=subtype or "octet-stream",
            filename=anhang.name,
        )

    with _connect(config) as server:
        server.send_message(msg)

    return message_id
