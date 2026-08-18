from __future__ import annotations

from pydantic import BaseModel


class SearchRequest(BaseModel):
    was: str = ""
    wo: str = ""
    umkreis: int = 25
    veroeffentlicht_seit: int | None = 14
    arbeitszeit: str | None = None
    size: int = 25


class SearchResponse(BaseModel):
    gefunden: int
    neu: int
    uebersprungen_unter_schwelle: int


class JobOut(BaseModel):
    id: int
    refnr: str
    titel: str
    firma: str
    ort: str
    url: str
    beschreibung: str
    veroeffentlicht_am: str
    match_score: int
    status: str

    model_config = {"from_attributes": True}


class JobAlertImportResponse(BaseModel):
    emails_gefunden: int
    emails_verarbeitet: int
    jobs_neu: int
    fehler: list[str]
    ungelesene_absender: list[str]
