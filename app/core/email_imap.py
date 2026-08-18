"""Status-Tracking per IMAP: Postfach auf Antworten zu Bewerbungen pruefen.

Nur ungelesene Mails werden betrachtet, und zwar per BODY.PEEK[] - das setzt
NICHT automatisch das \\Seen-Flag. Als gelesen markiert wird gezielt erst
eine Mail, die tatsaechlich einer Bewerbung zugeordnet werden konnte (siehe
status_tracking.py) - alle anderen, nicht zuordenbaren Mails im Postfach
bleiben unangetastet.
"""
from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass, field
from email.header import decode_header
from email.utils import getaddresses

_TIMEOUT = 20


class ImapError(Exception):
    pass


@dataclass
class ImapConfig:
    host: str
    port: int
    user: str
    password: str
    use_ssl: bool = True


@dataclass
class ParsedEmail:
    uid: bytes
    from_addr: str
    subject: str
    body: str
    message_id: str | None
    reference_ids: list[str] = field(default_factory=list)
    html: str = ""
    folder: str = "INBOX"


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def _decode_payload(part: email.message.Message) -> str:
    payload = part.get_payload(decode=True)
    if not payload:
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_bodies(msg: email.message.Message) -> tuple[str, str]:
    """Liefert (Klartext, HTML) der Mail. Job-Alert-Mails (LinkedIn/Xing/
    StepStone/Indeed) sind meist reines HTML - fuer deren Auswertung wird
    der HTML-Teil gebraucht, da darin die Stellenlinks stecken; fuer die
    einfache Schluesselwort-Klassifikation von Bewerbungsantworten reicht
    der Klartext."""
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_filename():
                continue
            if part.get_content_type() == "text/plain" and not plain:
                plain = _decode_payload(part)
            elif part.get_content_type() == "text/html" and not html:
                html = _decode_payload(part)
    elif msg.get_content_type() == "text/html":
        html = _decode_payload(msg)
    else:
        plain = _decode_payload(msg)
    return plain, html


_LIST_RESPONSE_RE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"(?P<delim>[^"]*)"|NIL)\s+(?P<name>.+)$')

# Ordner, die bewusst NICHT durchsucht werden - Postausgang/Entwuerfe/Papierkorb/
# Spam enthalten keine relevanten eingehenden Job-Alert- oder Antwort-Mails.
# Manche Provider (z.B. Web.de/GMX) melden das per IMAP SPECIAL-USE-Flag, andere
# nur ueber den (deutschen oder englischen) Ordnernamen - daher beide Wege.
_EXCLUDED_SPECIAL_USE_FLAGS = {"\\Trash", "\\Sent", "\\Drafts", "\\Junk"}
_EXCLUDED_FOLDER_NAMES = {
    "sent", "gesendet", "gesendete objekte", "gesendete elemente",
    "drafts", "entwuerfe", "entwürfe",
    "trash", "papierkorb", "geloeschte objekte", "gelöschte objekte", "deleted items",
    "junk", "spam", "junk-e-mail",
}


def _decode_list_line(raw: object) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _list_selectable_folders(conn: imaplib.IMAP4) -> list[str]:
    """Alle Postfach-Ordner ausser Sonderordnern (siehe oben). Faellt bei
    Problemen mit dem LIST-Kommando auf ['INBOX'] zurueck (altes Verhalten),
    damit ein einzelner unerwarteter Server niemals zum Totalausfall fuehrt."""
    status, data = conn.list()
    if status != "OK" or not data:
        return ["INBOX"]

    folders = []
    for raw in data:
        line = _decode_list_line(raw)
        if not line:
            continue
        match = _LIST_RESPONSE_RE.match(line)
        if not match:
            continue
        flags = match.group("flags")
        if "\\Noselect" in flags or any(f in flags for f in _EXCLUDED_SPECIAL_USE_FLAGS):
            continue
        name_raw = match.group("name").strip()
        name_plain = name_raw[1:-1] if name_raw.startswith('"') and name_raw.endswith('"') else name_raw
        if name_plain.strip().lower() in _EXCLUDED_FOLDER_NAMES:
            continue
        folders.append(name_raw)
    return folders or ["INBOX"]


class ImapClient:
    """Kontextmanager fuer eine IMAP-Session (Verbindungsaufbau, Abruf,
    gezieltes Markieren als gelesen, sauberes Schliessen)."""

    def __init__(self, config: ImapConfig) -> None:
        self.config = config
        self._conn: imaplib.IMAP4 | None = None

    def __enter__(self) -> "ImapClient":
        try:
            if self.config.use_ssl:
                self._conn = imaplib.IMAP4_SSL(self.config.host, self.config.port, timeout=_TIMEOUT)
            else:
                self._conn = imaplib.IMAP4(self.config.host, self.config.port, timeout=_TIMEOUT)
            self._conn.login(self.config.user, self.config.password)
            self._conn.select("INBOX")
        except (imaplib.IMAP4.error, OSError) as exc:
            raise ImapError(f"IMAP-Verbindung fehlgeschlagen: {exc}") from exc
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except imaplib.IMAP4.error:
                pass
            # Ein zuvor fehlgeschlagenes STORE (z.B. an einem schreibgeschuetzten
            # Ordner) hinterlaesst intern ein "READ-ONLY"-Merkmal, das imaplib erst
            # beim naechsten Kommando prueft - ohne diesen Schutz kann allein das
            # Aufraeumen beim Verbindungsende mit genau diesem Altlast-Fehler abbrechen.
            try:
                self._conn.logout()
            except imaplib.IMAP4.error:
                pass

    def fetch_unseen(self) -> list[ParsedEmail]:
        """Durchsucht ALLE Postfach-Ordner (ausser Sonderordnern, siehe
        _list_selectable_folders) nach ungelesenen Mails - nicht nur INBOX.
        Grund: Provider wie Web.de/GMX sortieren Mails unbekannter Absender
        (z.B. No-Reply-Adressen von Jobportalen) automatisch in einen
        eigenen IMAP-Ordner (etwa "Unbekannt") einsortiert, statt in INBOX."""
        assert self._conn is not None
        results: list[ParsedEmail] = []
        for folder in _list_selectable_folders(self._conn):
            try:
                results.extend(self._fetch_unseen_in_folder(folder))
            except imaplib.IMAP4.error:
                # Ein einzelner problematischer Ordner (z.B. unerwartete
                # Serverantworten bei virtuellen Kategorie-Ordnern) soll nicht
                # dazu fuehren, dass alle anderen Ordner uebersprungen werden.
                continue
        return results

    def _fetch_unseen_in_folder(self, folder: str) -> list[ParsedEmail]:
        assert self._conn is not None
        results: list[ParsedEmail] = []
        status, _ = self._conn.select(folder)
        if status != "OK":
            return results
        status, data = self._conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return results
        for uid in data[0].split():
            status, msg_data = self._conn.fetch(uid, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_addrs = getaddresses([msg.get("From", "")])
            from_addr = from_addrs[0][1] if from_addrs else ""

            references_raw = msg.get("References", "") + " " + msg.get("In-Reply-To", "")
            reference_ids = [r.strip() for r in references_raw.split() if r.strip()]

            plain, html = _extract_bodies(msg)
            results.append(
                ParsedEmail(
                    uid=uid,
                    from_addr=from_addr,
                    subject=_decode(msg.get("Subject")),
                    body=plain,
                    message_id=msg.get("Message-ID"),
                    reference_ids=reference_ids,
                    html=html,
                    folder=folder,
                )
            )
        return results

    def mark_seen(self, uid: bytes, folder: str = "INBOX") -> None:
        """Kann fehlschlagen, wenn folder serverseitig READ-ONLY ist (z.B.
        virtuelle Kategorie-Ordner wie Web.de's "Unbekannt"), da das Setzen
        des \\Seen-Flags dort grundsaetzlich nicht moeglich ist. Aufrufer
        sollten sich daher nicht allein auf diese Markierung verlassen, um
        Mehrfachverarbeitung zu vermeiden (siehe Message-ID-basiertes
        Tracking in job_alert_import.py)."""
        assert self._conn is not None
        try:
            self._conn.select(folder)
            typ, dat = self._conn.store(uid, "+FLAGS", "\\Seen")
        except imaplib.IMAP4.error as exc:
            raise ImapError(f"Konnte Mail in Ordner '{folder}' nicht als gelesen markieren: {exc}") from exc
        if typ != "OK":
            # store() wirft bei einer NO-Antwort (z.B. schreibgeschuetzter
            # Ordner) selbst KEINE Exception - ohne diese explizite Pruefung
            # wuerde ein fehlgeschlagenes Markieren unbemerkt durchrutschen.
            raise ImapError(f"Konnte Mail in Ordner '{folder}' nicht als gelesen markieren: {typ} {dat}")


KEYWORDS_EINLADUNG = [
    "vorstellungsgespraech",
    "vorstellungsgespräch",
    "einladen",
    "kennenlernen",
    "gespraechstermin",
    "gesprächstermin",
    "interview",
]
KEYWORDS_ABSAGE = [
    "absage",
    "leider",
    "andere kandidat",
    "andere bewerber",
    "nicht beruecksichtigen",
    "nicht berücksichtigen",
    "abgesagt",
]


def classify_reply(betreff: str, text: str) -> str:
    """Einfache Schluesselwort-Erkennung; der Nutzer kann das Ergebnis in der
    UI jederzeit manuell korrigieren (status_quelle wird dann auf 'manuell'
    gesetzt)."""
    combined = f"{betreff} {text}".lower()
    if any(kw in combined for kw in KEYWORDS_EINLADUNG):
        return "einladung"
    if any(kw in combined for kw in KEYWORDS_ABSAGE):
        return "absage"
    return "antwort_erhalten"
