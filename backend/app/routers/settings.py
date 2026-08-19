"""Einstellungen: Match-Schwelle, Claude-Modell, Auto-Versand, Zugangsdaten.

Buendelt Felder aus ProfileData (match_threshold, auto_send_enabled) und
UserCredentials (SMTP/IMAP/Claude) zu einer einzigen Ansicht, analog zum
Einstellungen-Tab der Desktop-App."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.email_smtp import SmtpConfig, SmtpError, test_connection
from app.database import get_db
from app.deps import get_current_user
from app.models.credentials import UserCredentials
from app.models.profile import ProfileData
from app.models.user import User
from app.schemas.settings import SettingsOut, SettingsUpdate, SmtpTestRequest, SmtpTestResult
from app.security import decrypt_secret, encrypt_secret

router = APIRouter(prefix="/settings", tags=["settings"])


def _load(db: Session, user_id: int) -> tuple[ProfileData, UserCredentials]:
    profile = db.query(ProfileData).filter(ProfileData.user_id == user_id).first()
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user_id).first()
    if profile is None or creds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil nicht gefunden.")
    return profile, creds


def _to_out(profile: ProfileData, creds: UserCredentials) -> SettingsOut:
    return SettingsOut(
        smtp_host=creds.smtp_host,
        smtp_port=creds.smtp_port,
        imap_host=creds.imap_host,
        imap_port=creds.imap_port,
        email_user=creds.email_user,
        has_email_password=bool(creds.email_password_enc),
        claude_model=creds.claude_model,
        imap_auto_check_enabled=creds.imap_auto_check_enabled,
        imap_auto_check_minutes=creds.imap_auto_check_minutes,
        match_threshold=profile.match_threshold,
        auto_send_enabled=profile.auto_send_enabled,
    )


@router.get("", response_model=SettingsOut)
def get_settings_view(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SettingsOut:
    profile, creds = _load(db, user.id)
    return _to_out(profile, creds)


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SettingsOut:
    profile, creds = _load(db, user.id)

    creds.smtp_host = payload.smtp_host
    creds.smtp_port = payload.smtp_port
    creds.imap_host = payload.imap_host
    creds.imap_port = payload.imap_port
    creds.email_user = payload.email_user
    if payload.email_password is not None:
        creds.email_password_enc = encrypt_secret(payload.email_password) if payload.email_password else None
    creds.claude_model = payload.claude_model
    creds.imap_auto_check_enabled = payload.imap_auto_check_enabled
    creds.imap_auto_check_minutes = payload.imap_auto_check_minutes

    profile.match_threshold = payload.match_threshold
    profile.auto_send_enabled = payload.auto_send_enabled

    db.commit()
    db.refresh(profile)
    db.refresh(creds)
    return _to_out(profile, creds)


@router.post("/test-smtp", response_model=SmtpTestResult)
def test_smtp(
    payload: SmtpTestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SmtpTestResult:
    """Testet die im Formular eingegebenen Werte (auch wenn noch nicht
    gespeichert) - leere Felder fallen auf die gespeicherten Zugangsdaten
    zurueck, damit ein Test auch ohne erneute Passworteingabe funktioniert."""
    _, creds = _load(db, user.id)

    host = payload.smtp_host or creds.smtp_host
    port = payload.smtp_port or creds.smtp_port
    email_user = payload.email_user or creds.email_user
    password = payload.email_password or decrypt_secret(creds.email_password_enc)

    if not (host and port and email_user and password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "SMTP-Zugangsdaten sind unvollstaendig.")

    config = SmtpConfig(host=host, port=port, user=email_user, password=password, use_ssl=port == 465)
    try:
        test_connection(config)
    except SmtpError as exc:
        return SmtpTestResult(erfolgreich=False, hinweis=str(exc))
    return SmtpTestResult(erfolgreich=True, hinweis="Verbindung erfolgreich hergestellt.")
