"""Profil-Verwaltung: Stammdaten, PDF-Import, Zuruecksetzen, Anlagen."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.profile_import import ProfileImportError, extract_profile_from_documents
from app.database import get_db
from app.deps import get_current_user
from app.models.attachment import Attachment
from app.models.credentials import UserCredentials
from app.models.profile import ProfileData
from app.models.user import User
from app.schemas.profile import (
    AttachmentOut,
    ProfileImportSuggestion,
    ProfileOut,
    ProfileUpdate,
)
from app.security import decrypt_secret

router = APIRouter(prefix="/profile", tags=["profile"])
settings = get_settings()


def _get_profile(db: Session, user_id: int) -> ProfileData:
    profile = db.query(ProfileData).filter(ProfileData.user_id == user_id).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil nicht gefunden.")
    return profile


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProfileData:
    return _get_profile(db, user.id)


@router.put("", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ProfileData:
    profile = _get_profile(db, user.id)
    profile.name = payload.name
    profile.adresse = payload.adresse
    profile.telefon = payload.telefon
    profile.email = payload.email
    profile.wunschjobtitel = payload.wunschjobtitel
    profile.wunschort = payload.wunschort
    profile.umkreis_km = payload.umkreis_km
    profile.arbeitszeit = payload.arbeitszeit
    profile.berufserfahrung = [e.model_dump() for e in payload.berufserfahrung]
    profile.ausbildung = [a.model_dump() for a in payload.ausbildung]
    profile.skills = payload.skills
    profile.sprachen = [s.model_dump() for s in payload.sprachen]
    profile.zertifikate = payload.zertifikate
    profile.cover_letter_hinweise = payload.cover_letter_hinweise
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/reset", response_model=ProfileOut)
def reset_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProfileData:
    profile = _get_profile(db, user.id)
    profile.name = user.display_name
    profile.adresse = ""
    profile.telefon = ""
    profile.email = user.email
    profile.wunschjobtitel = []
    profile.wunschort = ""
    profile.umkreis_km = 25
    profile.arbeitszeit = "vz"
    profile.berufserfahrung = []
    profile.ausbildung = []
    profile.skills = []
    profile.sprachen = []
    profile.zertifikate = []
    profile.cover_letter_hinweise = ""
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/import-pdf", response_model=ProfileImportSuggestion)
async def import_pdf(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user.id).first()
    api_key = decrypt_secret(creds.anthropic_api_key_enc) if creds else None
    if not api_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Kein Anthropic-API-Key hinterlegt. Bitte zuerst in den Einstellungen speichern.",
        )

    payload = [(f.filename or "dokument.pdf", await f.read()) for f in files]
    try:
        data = extract_profile_from_documents(api_key, payload, model=creds.claude_model if creds else None)
    except ProfileImportError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return data


@router.get("/attachments", response_model=list[AttachmentOut])
def list_attachments(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Attachment]:
    return db.query(Attachment).filter(Attachment.user_id == user.id).order_by(Attachment.uploaded_at).all()


@router.post("/attachments", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Attachment:
    data = await file.read()
    if len(data) > settings.max_attachment_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Datei ist groesser als {settings.max_attachment_bytes // (1024 * 1024)} MB.",
        )
    attachment = Attachment(
        user_id=user.id,
        filename=file.filename or "anlage.pdf",
        content_type=file.content_type or "application/pdf",
        size_bytes=len(data),
        data=data,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_attachment(
    attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.user_id == user.id)
        .first()
    )
    if attachment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anlage nicht gefunden.")
    db.delete(attachment)
    db.commit()
