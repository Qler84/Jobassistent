from __future__ import annotations

from pydantic import BaseModel


class SettingsOut(BaseModel):
    smtp_host: str | None
    smtp_port: int | None
    imap_host: str | None
    imap_port: int | None
    email_user: str | None
    has_email_password: bool
    claude_model: str
    imap_auto_check_enabled: bool
    imap_auto_check_minutes: int
    match_threshold: int
    auto_send_enabled: bool


class SettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
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


class SmtpTestRequest(BaseModel):
    """Testet die aktuell im Formular stehenden Werte, nicht zwingend die
    bereits gespeicherten - erlaubt 'Testen' vor dem 'Speichern'. Leere
    Felder fallen auf die gespeicherten Zugangsdaten zurueck."""
    smtp_host: str | None = None
    smtp_port: int | None = None
    email_user: str | None = None
    email_password: str | None = None


class SmtpTestResult(BaseModel):
    erfolgreich: bool
    hinweis: str
