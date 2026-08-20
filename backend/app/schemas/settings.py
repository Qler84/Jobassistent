from __future__ import annotations

from pydantic import BaseModel


class SettingsOut(BaseModel):
    imap_host: str | None
    imap_port: int | None
    email_user: str | None
    has_email_password: bool
    sender_verified: bool
    claude_model: str
    imap_auto_check_enabled: bool
    imap_auto_check_minutes: int
    match_threshold: int
    auto_send_enabled: bool


class SettingsUpdate(BaseModel):
    imap_host: str | None = None
    imap_port: int | None = None
    email_user: str | None = None
    # None = unveraendert lassen, "" = explizit loeschen
    email_password: str | None = None
    claude_model: str = "claude-sonnet-5"
    imap_auto_check_enabled: bool = False
    imap_auto_check_minutes: int = 30
    match_threshold: int = 20
    auto_send_enabled: bool = False


class SenderVerifyRequest(BaseModel):
    """Absenderadresse aus dem (evtl. noch ungespeicherten) Formular -
    erlaubt das Anstossen der Verifizierung vor dem 'Speichern'."""
    email_user: str | None = None
    sender_name: str | None = None


class SenderVerifyResult(BaseModel):
    verifiziert: bool
    hinweis: str
