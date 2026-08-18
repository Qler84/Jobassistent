"""Client fuer die Jobsuche-API der Bundesagentur fuer Arbeit.

Community-dokumentiert unter github.com/bundesAPI/jobsuche-api. Der
X-API-Key ist der oeffentliche, feste Schluessel, den auch die offizielle
Jobboerse-Website clientseitig verwendet - kein Registrierungsprozess noetig.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

import requests

from app.config import BA_API_BASE_URL, BA_API_KEY

_HEADERS = {"X-API-Key": BA_API_KEY, "User-Agent": "JobAssistant/1.0"}
_TIMEOUT = 15

# Mapping ausgeschriebener Werte -> API-Kuerzel (arbeitszeit)
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
    params: dict[str, object] = {
        "was": was,
        "angebotsart": angebotsart,
        "size": size,
        "page": 1,
    }
    if wo:
        params["wo"] = wo
        params["umkreis"] = umkreis
    if veroeffentlicht_seit is not None:
        params["veroeffentlichtseit"] = veroeffentlicht_seit
    if arbeitszeit:
        params["arbeitszeit"] = arbeitszeit

    try:
        resp = requests.get(
            f"{BA_API_BASE_URL}pc/v4/jobs", params=params, headers=_HEADERS, timeout=_TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
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
        resp = requests.get(
            f"{BA_API_BASE_URL}pc/v4/jobdetails/{encoded}", headers=_HEADERS, timeout=_TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
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
