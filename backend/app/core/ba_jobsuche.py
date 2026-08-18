"""Client fuer die Jobsuche-API der Bundesagentur fuer Arbeit.

Unveraendert aus der Desktop-App uebernommen (community-dokumentiert unter
github.com/bundesAPI/jobsuche-api, oeffentlicher Key ohne Registrierung).
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import get_settings

settings = get_settings()
_HEADERS = {"X-API-Key": settings.ba_api_key, "User-Agent": "JobAssistent-Web/1.0"}
_TIMEOUT = 15

ARBEITSZEIT_CODES = {
    "Vollzeit": "vz",
    "Teilzeit": "tz",
    "Schicht/Nacht/Wochenende": "snw",
    "Home-Office": "ho",
    "Minijob": "mj",
}


class BAApiError(Exception):
    pass


@dataclass
class JobSearchResult:
    refnr: str
    titel: str
    arbeitgeber: str
    ort: str
    url: str
    veroeffentlicht_am: str


@dataclass
class JobDetails:
    refnr: str
    beschreibung: str
    arbeitgeber: str
    ort: str
    url: str


def _job_frontend_url(refnr: str) -> str:
    return f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}"


def search_jobs(
    was: str,
    wo: str = "",
    umkreis: int = 25,
    veroeffentlicht_seit: Optional[int] = None,
    arbeitszeit: Optional[str] = None,
    angebotsart: int = 1,
    size: int = 25,
) -> list[JobSearchResult]:
    params: dict[str, object] = {"was": was, "angebotsart": angebotsart, "size": size, "page": 1}
    if wo:
        params["wo"] = wo
        params["umkreis"] = umkreis
    if veroeffentlicht_seit is not None:
        params["veroeffentlichtseit"] = veroeffentlicht_seit
    if arbeitszeit:
        params["arbeitszeit"] = arbeitszeit

    try:
        resp = httpx.get(
            f"{settings.ba_api_base_url}pc/v4/jobs", params=params, headers=_HEADERS, timeout=_TIMEOUT
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BAApiError(f"Jobsuche-API nicht erreichbar: {exc}") from exc

    data = resp.json()
    results = []
    for item in data.get("stellenangebote", []):
        arbeitsort = item.get("arbeitsort") or {}
        ort = ", ".join(filter(None, [arbeitsort.get("plz"), arbeitsort.get("ort")]))
        refnr = item.get("refnr", "")
        results.append(
            JobSearchResult(
                refnr=refnr,
                titel=item.get("titel") or item.get("beruf") or "",
                arbeitgeber=item.get("arbeitgeber", ""),
                ort=ort,
                url=item.get("externeUrl") or _job_frontend_url(refnr),
                veroeffentlicht_am=item.get("aktuelleVeroeffentlichungsdatum", ""),
            )
        )
    return results


def get_job_details(refnr: str) -> JobDetails:
    encoded = base64.b64encode(refnr.encode("utf-8")).decode("utf-8")
    try:
        resp = httpx.get(
            f"{settings.ba_api_base_url}pc/v4/jobdetails/{encoded}", headers=_HEADERS, timeout=_TIMEOUT
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BAApiError(f"Jobdetails nicht abrufbar: {exc}") from exc

    data = resp.json()
    arbeitsorte = data.get("arbeitsorte") or [{}]
    erster_ort = arbeitsorte[0] if arbeitsorte else {}
    ort = ", ".join(filter(None, [erster_ort.get("plz"), erster_ort.get("ort")]))
    return JobDetails(
        refnr=refnr,
        beschreibung=data.get("stellenangebotsBeschreibung", ""),
        arbeitgeber=data.get("arbeitgeber", ""),
        ort=ort,
        url=data.get("allianzpartnerUrl") or _job_frontend_url(refnr),
    )
