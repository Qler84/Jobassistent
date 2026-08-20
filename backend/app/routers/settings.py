"""Einstellungen: Match-Schwelle, Claude-Modell, Auto-Versand, Zugangsdaten.

Buendelt Felder aus ProfileData (match_threshold, auto_send_enabled) und
UserCredentials (IMAP/Claude) zu einer einzigen Ansicht, analog zum
Einstellungen-Tab der Desktop-App. Der E-Mail-Versand selbst laeuft ueber
die globale Brevo-API (core/email_send.py), nicht mehr ueber vom Nutzer
hinterlegte SMTP-Zugangsdaten - dafuer muss dessen Absenderadresse einmalig
bei Brevo verifiziert werden."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.email_send import EmailApiError, ensure_sender, sender_verified
from app.database import get_db
from app.deps import get_current_user
from app.models.credentials import UserCredentials
from app.models.profile import ProfileData
from app.models.user import User
from app.schemas.settings import SenderVerifyRequest, SenderVerifyResult, SettingsOut, SettingsUpdate
from app.security import encrypt_secret

router = APIRouter(prefix="/settings", tags=["settings"])
settings = get_settings()


def _load(db: Session, user_id: int) -> tuple[ProfileData, UserCredentials]:
    profile = db.query(ProfileData).filter(ProfileData.user_id == user_id).first()
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user_id).first()
    if profile is None or creds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil nicht gefunden.")
    return profile, creds


def _to_out(profile: ProfileData, creds: UserCredentials) -> SettingsOut:
    verified = bool(creds.email_user) and sender_verified(settings.brevo_api_key, creds.email_user)
    return SettingsOut(
        imap_host=creds.imap_host,
        imap_port=creds.imap_port,
        email_user=creds.email_user,
        has_email_password=bool(creds.email_password_enc),
        sender_verified=verified,
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


@router.post("/verify-sender", response_model=SenderVerifyResult)
def verify_sender(
    payload: SenderVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SenderVerifyResult:
    """Legt die Absenderadresse bei Brevo an (idempotent) und loest damit die
    Bestaetigungs-E-Mail aus, bzw. meldet, falls bereits verifiziert."""
    profile, creds = _load(db, user.id)
    email = payload.email_user or creds.email_user
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "E-Mail-Adresse fehlt.")

    if sender_verified(settings.brevo_api_key, email):
        return SenderVerifyResult(verifiziert=True, hinweis="Absenderadresse ist bereits verifiziert.")

    try:
        ensure_sender(settings.brevo_api_key, email, payload.sender_name or profile.name)
    except EmailApiError as exc:
        return SenderVerifyResult(verifiziert=False, hinweis=str(exc))

    return SenderVerifyResult(
        verifiziert=False,
        hinweis=f"Bestaetigungs-E-Mail wurde an {email} gesendet. Bitte Posteingang pruefen und Link anklicken.",
    )
