"""Bewerbungen: Anschreiben-Generierung, Freigabe, Versand, Status-Tracking.

Sicherheitsprinzip aus der Desktop-App unveraendert: ein Anschreiben wird nie
automatisch generiert (nur nach Klick auf 'Bestaetigen' bei einer
Stellenanzeige) und nie automatisch versendet (nur nach explizitem Klick auf
'Freigeben & Senden' UND nur, wenn der Nutzer den automatischen Versand in
den Einstellungen ueberhaupt aktiviert hat - der Vorschau-Modus ist
Standard)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.cover_letter import CoverLetterError, extract_contact_email, generate_cover_letter
from app.core.email_imap import ImapConfig
from app.core.email_smtp import SmtpConfig, SmtpError, send_application_email
from app.core.status_tracking import run_imap_check
from app.database import get_db
from app.deps import get_current_user
from app.models.application import Application
from app.models.attachment import Attachment
from app.models.credentials import UserCredentials
from app.models.job import Job
from app.models.profile import ProfileData
from app.models.user import User
from app.schemas.application import (
    ApplicationOut,
    ApplicationUpdate,
    CoverLetterGenerateResponse,
    ImapCheckResult,
    SendResult,
)
from app.security import decrypt_secret

router = APIRouter(tags=["applications"])


def _get_job(db: Session, user_id: int, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stellenanzeige nicht gefunden.")
    return job


def _get_application(db: Session, user_id: int, application_id: int) -> Application:
    application = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == application_id, Application.user_id == user_id)
        .first()
    )
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bewerbung nicht gefunden.")
    return application


@router.post("/jobs/{job_id}/confirm", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def confirm_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Application:
    job = _get_job(db, user.id, job_id)
    job.status = "bestaetigt"
    application = Application(user_id=user.id, job_id=job.id, status="entwurf", status_quelle="manuell")
    db.add(application)
    db.commit()
    return _get_application(db, user.id, application.id)


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    status_filter: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Application]:
    query = db.query(Application).options(joinedload(Application.job)).filter(Application.user_id == user.id)
    if status_filter:
        query = query.filter(Application.status == status_filter)
    return query.order_by(Application.erstellt_am.desc()).all()


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Application:
    return _get_application(db, user.id, application_id)


@router.post("/applications/{application_id}/generate-cover-letter", response_model=CoverLetterGenerateResponse)
def generate_letter(
    application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CoverLetterGenerateResponse:
    application = _get_application(db, user.id, application_id)
    job = application.job
    profile = db.query(ProfileData).filter(ProfileData.user_id == user.id).first()
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user.id).first()
    api_key = decrypt_secret(creds.anthropic_api_key_enc) if creds else None
    if not api_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Kein Anthropic-API-Key hinterlegt. Bitte zuerst in den Einstellungen speichern.",
        )

    try:
        result = generate_cover_letter(
            profile,
            api_key,
            job_titel=job.titel,
            arbeitgeber=job.firma,
            ort=job.ort,
            beschreibung=job.beschreibung,
            ansprechpartner=application.ansprechpartner,
            model=creds.claude_model if creds else None,
        )
    except CoverLetterError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    application.anschreiben_text = result.text
    if result.erkannter_ansprechpartner:
        application.ansprechpartner = result.erkannter_ansprechpartner
    if not application.kontakt_email:
        application.kontakt_email = extract_contact_email(job.beschreibung)
    if not application.betreff:
        application.betreff = f"Bewerbung als {job.titel}"
    db.commit()

    return CoverLetterGenerateResponse(
        anschreiben_text=application.anschreiben_text,
        ansprechpartner=application.ansprechpartner,
        kontakt_email=application.kontakt_email,
        betreff=application.betreff,
    )


@router.put("/applications/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Application:
    application = _get_application(db, user.id, application_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(application, key, value)
    db.commit()
    return _get_application(db, user.id, application_id)


@router.post("/applications/{application_id}/send", response_model=SendResult)
def send_application(
    application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SendResult:
    application = _get_application(db, user.id, application_id)
    profile = db.query(ProfileData).filter(ProfileData.user_id == user.id).first()
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user.id).first()

    if not (profile and profile.auto_send_enabled):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Der automatische Versand ist in den Einstellungen deaktiviert. Aktiviere ihn zuerst, "
            "um Bewerbungen tatsaechlich zu versenden (Vorschau-Modus ist Standard).",
        )
    if not application.anschreiben_text or not application.kontakt_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Anschreiben-Text oder Empfaenger-E-Mail fehlt.")

    password = decrypt_secret(creds.email_password_enc) if creds else None
    if not (creds and creds.smtp_host and creds.smtp_port and creds.email_user and password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "SMTP-Zugangsdaten sind unvollstaendig.")

    attachments = db.query(Attachment).filter(Attachment.user_id == user.id).all()
    anhaenge = [(a.filename, a.content_type, a.data) for a in attachments]

    config = SmtpConfig(
        host=creds.smtp_host,
        port=creds.smtp_port,
        user=creds.email_user,
        password=password,
        use_ssl=creds.smtp_port == 465,
    )
    try:
        message_id = send_application_email(
            config,
            empfaenger=application.kontakt_email,
            betreff=application.betreff or f"Bewerbung als {application.job.titel}",
            text=application.anschreiben_text,
            anhaenge=anhaenge,
            absender_name=profile.name,
        )
    except SmtpError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    application.status = "versendet"
    application.status_quelle = "manuell"
    application.versendet_am = datetime.now(timezone.utc)
    application.message_id = message_id
    db.commit()

    return SendResult(versendet=True, hinweis="Bewerbung wurde erfolgreich versendet.")


@router.post("/applications/check-inbox", response_model=ImapCheckResult)
def check_inbox(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ImapCheckResult:
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user.id).first()
    password = decrypt_secret(creds.email_password_enc) if creds else None
    if not (creds and creds.imap_host and creds.imap_port and creds.email_user and password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "IMAP-Zugangsdaten sind unvollstaendig.")

    config = ImapConfig(
        host=creds.imap_host,
        port=creds.imap_port,
        user=creds.email_user,
        password=password,
        use_ssl=creds.imap_port == 993,
    )
    try:
        updates = run_imap_check(config, db, user.id)
    except Exception as exc:  # ImapError aus email_imap.py, bewusst breit gefangen
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"IMAP-Fehler: {exc}") from exc

    details = [f"{u.betreff} ({u.von_status} -> {u.neuer_status})" for u in updates]
    return ImapCheckResult(aktualisiert=len(updates), details=details)
