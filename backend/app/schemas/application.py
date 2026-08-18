from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.job import JobOut


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    anschreiben_text: str | None
    betreff: str | None
    kontakt_email: str | None
    ansprechpartner: str | None
    status: str
    status_quelle: str
    erstellt_am: datetime
    versendet_am: datetime | None
    job: JobOut

    model_config = {"from_attributes": True}


class ApplicationUpdate(BaseModel):
    anschreiben_text: str | None = None
    betreff: str | None = None
    kontakt_email: str | None = None
    ansprechpartner: str | None = None
    status: str | None = None


class CoverLetterGenerateResponse(BaseModel):
    anschreiben_text: str
    ansprechpartner: str | None
    kontakt_email: str | None
    betreff: str


class SendResult(BaseModel):
    versendet: bool
    hinweis: str


class ImapCheckResult(BaseModel):
    aktualisiert: int
    details: list[str]
