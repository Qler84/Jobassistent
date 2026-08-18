"""Versand von Bewerbungen per SMTP.

Portiert aus der Desktop-App. Einziger Unterschied: Anlagen kommen als
(dateiname, content_type, bytes)-Tupel aus der DB statt von der lokalen
Festplatte gelesen zu werden."""
from __future__ import annotations

import smtplib
from contextlib import contextmanager
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Iterator

_TIMEOUT = 30

_TIMEOUT_HINWEIS = (
    "Zeitueberschreitung beim Verbindungsaufbau zum SMTP-Server. Moegliche Ursachen: "
    "(1) Server/Port falsch (Port 465 = SSL, jeder andere Port z.B. 587 = STARTTLS). "
    "(2) Der Mail-Provider blockiert die Verbindung von diesem Server aus."
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
    with _connect(config):
        pass


def send_application_email(
    config: SmtpConfig,
    empfaenger: str,
    betreff: str,
    text: str,
    anhaenge: list[tuple[str, str, bytes]],
    absender_name: str = "",
) -> str:
    """`anhaenge`: Liste von (dateiname, content_type, bytes). Gibt die
    erzeugte Message-ID zurueck (wird gespeichert, um spaeter per IMAP
    Antworten zuverlaessig zuzuordnen)."""
    absender_domain = config.user.split("@", 1)[-1] if "@" in config.user else None

    msg = EmailMessage()
    msg["From"] = f"{absender_name} <{config.user}>" if absender_name else config.user
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    msg["Date"] = formatdate(localtime=True)
    message_id = make_msgid(domain=absender_domain)
    msg["Message-ID"] = message_id
    msg.set_content(text)

    for filename, content_type, data in anhaenge:
        maintype, _, subtype = (content_type or "application/octet-stream").partition("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)

    with _connect(config) as server:
        server.send_message(msg)

    return message_id
