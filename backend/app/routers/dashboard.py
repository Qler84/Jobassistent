"""Dashboard-Kennzahlen und Kurzübersicht fuer die Startseite."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DashboardSummary:
    neue_treffer = db.query(Job).filter(Job.user_id == user.id, Job.status == "neu").count()
    versendet = db.query(Application).filter(Application.user_id == user.id, Application.status == "versendet").count()
    einladungen = db.query(Application).filter(Application.user_id == user.id, Application.status == "einladung").count()
    absagen = db.query(Application).filter(Application.user_id == user.id, Application.status == "absage").count()

    neue_matches = (
        db.query(Job)
        .filter(Job.user_id == user.id, Job.status == "neu")
        .order_by(Job.match_score.desc(), Job.first_seen.desc())
        .limit(5)
        .all()
    )
    letzte_aktivitaet = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.user_id == user.id)
        .order_by(Application.erstellt_am.desc())
        .limit(5)
        .all()
    )

    return DashboardSummary(
        neue_treffer=neue_treffer,
        versendet=versendet,
        einladungen=einladungen,
        absagen=absagen,
        neue_matches=neue_matches,
        letzte_aktivitaet=letzte_aktivitaet,
    )
