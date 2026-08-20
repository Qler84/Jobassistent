"""Versand von Bewerbungen ueber die Brevo Transactional-Email-API (HTTPS).

Ersetzt den fruehreren rohen SMTP-Versand: Render blockiert auf dem
kostenlosen Tier seit September 2025 ausgehende Verbindungen zu SMTP-Ports
(25/465/587) komplett - unabhaengig von Zugangsdaten. Die Brevo-API laeuft
ueber normales HTTPS (Port 443) und ist davon nicht betroffen.

Der API-Key ist global (ein Konto, vom Betreiber bezahlt/verwaltet - siehe
config.py), der tatsaechliche Absender bleibt aber pro Nutzer dessen eigene
Postfachadresse. Damit Brevo nicht im Namen fremder Adressen versendet, muss
jede Absenderadresse einmalig verifiziert werden (Bestaetigungslink, den
Brevo automatisch verschickt, sobald der Absender angelegt wird)."""
from __future__ import annotations

import base64
from email.utils import make_msgid

import httpx

_API_BASE = "https://api.brevo.com/v3"
_TIMEOUT = 20


class EmailApiError(Exception):
    pass


def _headers(api_key: str) -> dict[str, str]:
    return {"api-key": api_key, "content-type": "application/json", "accept": "application/json"}


def ensure_sender(api_key: str, email: str, name: str) -> None:
    """Legt den Absender bei Brevo an (falls noch nicht vorhanden) und loest
    damit die automatische Bestaetigungs-E-Mail an genau diese Adresse aus."""
    try:
        resp = httpx.post(
            f"{_API_BASE}/senders",
            headers=_headers(api_key),
            json={"name": name or email, "email": email},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise EmailApiError(f"Verbindung zum E-Mail-Dienst fehlgeschlagen: {exc}") from exc

    if resp.status_code == 201:
        return
    # Absender existiert bereits (z.B. erneuter Klick auf "Verifizierung anstossen") - kein Fehler.
    if resp.status_code == 400 and "duplicate" in resp.text.lower():
        return
    raise EmailApiError(f"Absender konnte nicht angelegt werden: {resp.text}")


def sender_verified(api_key: str, email: str) -> bool:
    """True, sobald der Nutzer den Bestaetigungslink von Brevo angeklickt hat."""
    try:
        resp = httpx.get(f"{_API_BASE}/senders", headers=_headers(api_key), timeout=_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError:
        return False
    for sender in resp.json().get("senders", []):
        if sender.get("email", "").lower() == email.lower():
            return bool(sender.get("active"))
    return False


def send_application_email(
    api_key: str,
    sender_email: str,
    sender_name: str,
    empfaenger: str,
    betreff: str,
    text: str,
    anhaenge: list[tuple[str, str, bytes]],
) -> str:
    """Gibt die erzeugte Message-ID zurueck (wird gespeichert, um spaeter per
    IMAP Antworten zuverlaessig zuzuordnen, siehe status_tracking.py)."""
    message_id = make_msgid()
    payload: dict = {
        "sender": {"email": sender_email, "name": sender_name or sender_email},
        "to": [{"email": empfaenger}],
        "subject": betreff,
        "textContent": text,
        "headers": {"Message-Id": message_id},
    }
    if anhaenge:
        payload["attachment"] = [
            {"name": filename, "content": base64.b64encode(data).decode("ascii")}
            for filename, _content_type, data in anhaenge
        ]

    try:
        resp = httpx.post(f"{_API_BASE}/smtp/email", headers=_headers(api_key), json=payload, timeout=30)
    except httpx.HTTPError as exc:
        raise EmailApiError(f"Verbindung zum E-Mail-Dienst fehlgeschlagen: {exc}") from exc

    if resp.status_code >= 400:
        raise EmailApiError(_friendly_error(sender_email, resp))
    return message_id


def _friendly_error(sender_email: str, resp: httpx.Response) -> str:
    try:
        data = resp.json()
        message = str(data.get("message", resp.text))
    except ValueError:
        return f"Versand fehlgeschlagen ({resp.status_code}): {resp.text}"

    lowered = message.lower()
    if "sender" in lowered and ("not" in lowered or "invalid" in lowered):
        return (
            f"Versand fehlgeschlagen: Die Absenderadresse {sender_email} ist bei Brevo noch nicht "
            "verifiziert. Bitte den Bestaetigungslink in der E-Mail von Brevo anklicken (siehe "
            "Einstellungen -> Absender-Verifizierung)."
        )
    if "credit" in lowered:
        return "Versand fehlgeschlagen: Das E-Mail-Kontingent des Betreibers ist aufgebraucht."
    return f"Versand fehlgeschlagen: {message}"
