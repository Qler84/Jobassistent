"""Stellensuche: BA-Jobsuche-API, Job-Alert-E-Mail-Import, Vorschlagsliste."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import ba_jobsuche, matching
from app.core.ba_jobsuche import BAApiError
from app.core.email_imap import ImapConfig
from app.core.job_alert_import import JobAlertImportError, run_job_alert_import
from app.database import get_db
from app.deps import get_current_user
from app.models.credentials import UserCredentials
from app.models.job import Job
from app.models.profile import ProfileData
from app.models.user import User
from app.schemas.job import JobAlertImportResponse, JobOut, SearchRequest, SearchResponse
from app.security import decrypt_secret

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_profile(db: Session, user_id: int) -> ProfileData:
    profile = db.query(ProfileData).filter(ProfileData.user_id == user_id).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil nicht gefunden.")
    return profile


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SearchResponse:
    profile = _get_profile(db, user.id)

    suchbegriffe = [payload.was] if payload.was else list(profile.wunschjobtitel or [])
    if not suchbegriffe:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Kein Suchbegriff angegeben und keine Wunschjobtitel im Profil hinterlegt.",
        )

    gefunden = 0
    neu = 0
    uebersprungen = 0
    now = datetime.now(timezone.utc)

    for was in suchbegriffe:
        try:
            results = ba_jobsuche.search_jobs(
                was=was,
                wo=payload.wo,
                umkreis=payload.umkreis,
                veroeffentlicht_seit=payload.veroeffentlicht_seit,
                arbeitszeit=payload.arbeitszeit,
                size=payload.size,
            )
        except BAApiError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        gefunden += len(results)
        for result in results:
            exists = db.query(Job).filter(Job.user_id == user.id, Job.refnr == result.refnr).first()
            if exists:
                continue
            try:
                details = ba_jobsuche.get_job_details(result.refnr)
                beschreibung = details.beschreibung
            except BAApiError:
                beschreibung = ""

            score = matching.score_job(profile, result.titel, beschreibung)
            if score < profile.match_threshold:
                uebersprungen += 1
                continue

            db.add(
                Job(
                    user_id=user.id,
                    refnr=result.refnr,
                    titel=result.titel,
                    firma=result.arbeitgeber,
                    ort=result.ort,
                    url=result.url,
                    beschreibung=beschreibung,
                    veroeffentlicht_am=result.veroeffentlicht_am,
                    match_score=score,
                    status="neu",
                    first_seen=now,
                )
            )
            neu += 1
    db.commit()
    return SearchResponse(gefunden=gefunden, neu=neu, uebersprungen_unter_schwelle=uebersprungen)


@router.get("", response_model=list[JobOut])
def list_jobs(
    status_filter: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Job]:
    query = db.query(Job).filter(Job.user_id == user.id)
    if status_filter:
        query = query.filter(Job.status == status_filter)
    return query.order_by(Job.match_score.desc(), Job.first_seen.desc()).all()


def _get_job(db: Session, user_id: int, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stellenanzeige nicht gefunden.")
    return job


@router.post("/{job_id}/reject", response_model=JobOut)
def reject_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Job:
    job = _get_job(db, user.id, job_id)
    job.status = "abgelehnt"
    db.commit()
    db.refresh(job)
    return job


@router.post("/import-alerts", response_model=JobAlertImportResponse)
def import_alerts(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> JobAlertImportResponse:
    profile = _get_profile(db, user.id)
    creds = db.query(UserCredentials).filter(UserCredentials.user_id == user.id).first()
    if creds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zugangsdaten nicht gefunden.")

    password = decrypt_secret(creds.email_password_enc)
    api_key = decrypt_secret(creds.anthropic_api_key_enc)
    if not (creds.imap_host and creds.imap_port and creds.email_user and password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "IMAP-Zugangsdaten sind unvollstaendig.")
    if not api_key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kein Anthropic-API-Key hinterlegt.")

    imap_config = ImapConfig(
        host=creds.imap_host,
        port=creds.imap_port,
        user=creds.email_user,
        password=password,
        use_ssl=creds.imap_port == 993,
    )
    try:
        result = run_job_alert_import(
            imap_config, profile, db, user.id, api_key, model=creds.claude_model
        )
    except JobAlertImportError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except Exception as exc:  # ImapError kommt aus email_imap, bewusst breit gefangen
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"IMAP-Fehler: {exc}") from exc

    return JobAlertImportResponse(**result.__dict__)
