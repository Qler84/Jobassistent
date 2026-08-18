from __future__ import annotations

from pydantic import BaseModel

from app.schemas.application import ApplicationOut
from app.schemas.job import JobOut


class DashboardSummary(BaseModel):
    neue_treffer: int
    versendet: int
    einladungen: int
    absagen: int
    neue_matches: list[JobOut]
    letzte_aktivitaet: list[ApplicationOut]
