"""Client fuer die Jobsuche-API der Bundesagentur fuer Arbeit.

Community-dokumentiert unter github.com/bundesAPI/jobsuche-api, oeffentlicher
Key ohne Registrierung. Die Such-Endpunktversion und mehrere Feldnamen im
JSON haben sich seit der urspruenglichen Desktop-App-Implementierung
geaendert (Suche: pc/v4/jobs -> pc/v6/jobs mit neuem Antwortschema;
Jobdetails: URL-Version pc/v4 unveraendert, aber "arbeitgeber"/"arbeitsorte"
wurden serverseitig zu "firma"/"stellenlokationen" umbenannt) - siehe
_parse_stellenlokation() fuer die gemeinsame Ortslogik beider Endpunkte."""
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


def _normalize_url(url: str | None, fallback: str) -> str:
    if not url:
        return fallback
    return url if url.startswith("http") else f"https://{url}"


def _first_ort(stellenlokationen: list[dict] | None) -> str:
    """Extrahiert 'PLZ Ort' aus dem ersten Eintrag von stellenlokationen
    (Liste von {"adresse": {"plz", "ort", ...}}) - Struktur ist bei
    Suchergebnissen und Jobdetails identisch."""
    if not stellenlokationen:
        return ""
    adresse = stellenlokationen[0].get("adresse") or {}
    return ", ".join(filter(None, [adresse.get("plz"), adresse.get("ort")]))


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
            f"{settings.ba_api_base_url}pc/v6/jobs", params=params, headers=_HEADERS, timeout=_TIMEOUT
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BAApiError(f"Jobsuche-API nicht erreichbar: {exc}") from exc

    data = resp.json()
    results = []
    for item in data.get("ergebnisliste", []):
        refnr = item.get("referenznummer", "")
        results.append(
            JobSearchResult(
                refnr=refnr,
                titel=item.get("stellenangebotsTitel") or item.get("hauptberuf") or "",
                arbeitgeber=item.get("firma", ""),
                ort=_first_ort(item.get("stellenlokationen")),
                url=_normalize_url(item.get("externeURL"), _job_frontend_url(refnr)),
                veroeffentlicht_am=item.get("datumErsteVeroeffentlichung", ""),
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
    return JobDetails(
        refnr=refnr,
        beschreibung=data.get("stellenangebotsBeschreibung", ""),
        arbeitgeber=data.get("firma", ""),
        ort=_first_ort(data.get("stellenlokationen")),
        url=_normalize_url(data.get("allianzpartnerUrl"), _job_frontend_url(refnr)),
    )
