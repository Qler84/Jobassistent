"""Import von Stellenangeboten aus Job-Alert-E-Mails (LinkedIn, Xing,
StepStone, Indeed, ...).

Ausdruecklich KEIN Scraping der Plattformen selbst: es werden ausschliesslich
E-Mails ausgewertet, die diese Portale ihrem Nutzer ohnehin regulaer als
"Job-Alert"/gespeicherte Suche zuschicken (offizielle Funktion der Portale,
vom Nutzer selbst eingerichtet). Der IMAP-Zugriff nutzt dieselben
Zugangsdaten wie das Status-Tracking in status_tracking.py.

Die HTML-Struktur solcher Digest-Mails unterscheidet sich pro Anbieter und
aendert sich mit der Zeit - statt fragiler, anbieterspezifischer HTML-Parser
uebernimmt Claude die Extraktion der einzelnen Stellenangebote aus dem
E-Mail-Inhalt (aehnliches Vorgehen wie beim PDF-Profil-Import).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import anthropic

from app.config import DEFAULT_CLAUDE_MODEL
from app.core import matching
from app.core.database import Database
from app.core.email_imap import ImapClient, ImapConfig, ImapError, ParsedEmail
from app.core.profile import Profile

# Absender-Domains bekannter Job-Alert-Mails. Erweiterbar - unbekannte
# Absender werden schlicht ignoriert (bleiben ungelesen, kein Fehler).
JOB_ALERT_SENDER_DOMAINS = [
    "linkedin.com",
    "xing.com",
    "stepstone.de",
    "stepstone.at",
    "stepstone.co.uk",
    "indeed.com",
    "indeed.de",
]

_MAX_CONTENT_CHARS = 50_000


class JobAlertImportError(Exception):
    pass


@dataclass
class JobAlertResult:
    emails_gefunden: int = 0
    emails_verarbeitet: int = 0
    jobs_neu: int = 0
    fehler: list[str] = field(default_factory=list)
    # Absender aller ungelesenen Mails im Postfach (unabhaengig vom
    # Domain-Filter) - reine Diagnose-Info fuer den Fall, dass gefunden=0
    # ist und unklar bleibt, ob das Postfach leer war oder der Absender
    # nicht als Job-Alert-Quelle erkannt wurde.
    ungelesene_absender: list[str] = field(default_factory=list)


def _is_job_alert_sender(from_addr: str) -> bool:
    domain = from_addr.lower().rsplit("@", 1)[-1] if "@" in from_addr else ""
    return any(domain == d or domain.endswith("." + d) for d in JOB_ALERT_SENDER_DOMAINS)


def _clean_html(html: str) -> str:
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r'src="data:image[^"]*"', 'src=""', html, flags=re.IGNORECASE)
    return html[:_MAX_CONTENT_CHARS]


def _make_refnr(url: str, titel: str, firma: str) -> str:
    basis = url.strip() or f"{titel.strip().lower()}|{firma.strip().lower()}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]
    return f"mail:{digest}"


_EXTRACTION_PROMPT = """Der folgende Inhalt ist eine Job-Alert-Benachrichtigungs-E-Mail eines
Jobportals (LinkedIn, Xing, StepStone oder Indeed). Sie enthaelt eine Liste einzelner
Stellenangebote.

Extrahiere ALLE darin enthaltenen einzelnen Stellenangebote. Antworte AUSSCHLIESSLICH mit
einem JSON-Array (keine Erklaerungen, kein Markdown, keine Codebloecke), exakt in diesem
Format - bei keinen erkennbaren Stellenangeboten gib ein leeres Array [] zurueck:

[
  {{"titel": "...", "firma": "...", "ort": "...", "url": "Link zur Stellenanzeige, falls vorhanden, sonst leerer String", "beschreibung": "kurze Zusammenfassung/Snippet falls vorhanden, sonst leerer String"}}
]

E-Mail-Betreff: {subject}

E-Mail-Inhalt:
{content}"""


def _extract_json_array(text: str) -> list[dict]:
    match = re.search(r"\[.*\]", text.strip(), re.DOTALL)
    if not match:
        raise JobAlertImportError("Claude hat kein verwertbares JSON-Array zurueckgegeben.")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JobAlertImportError(f"Antwort von Claude war kein gueltiges JSON: {exc}") from exc
    if not isinstance(data, list):
        raise JobAlertImportError("Claude-Antwort war kein JSON-Array.")
    return data


def extract_jobs_from_email(api_key: str, subject: str, content: str, model: str) -> list[dict]:
    if not content.strip():
        return []
    client = anthropic.Anthropic(api_key=api_key)
    prompt = _EXTRACTION_PROMPT.format(subject=subject, content=content)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        raise JobAlertImportError(f"Claude-API-Fehler: {exc}") from exc

    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json_array(text)


def run_job_alert_import(
    imap_config: ImapConfig,
    profile: Profile,
    db: Database,
    api_key: str,
    model: str = DEFAULT_CLAUDE_MODEL,
) -> JobAlertResult:
    """Prueft ungelesene Job-Alert-Mails, extrahiert per Claude die darin
    enthaltenen Stellenangebote, bewertet sie mit dem gleichen Match-Scoring
    wie die BA-Jobsuche und speichert Treffer oberhalb der Match-Schwelle.
    Nur erfolgreich verarbeitete Mails werden als gelesen markiert - Mails,
    bei denen die Extraktion fehlschlaegt, bleiben ungelesen und erscheinen
    beim naechsten Durchlauf erneut (sichtbar im Fehlerbericht)."""
    result = JobAlertResult()
    now_iso = datetime.now(timezone.utc).isoformat()

    with ImapClient(imap_config) as client:
        alle_mails: list[ParsedEmail] = client.fetch_unseen()
        result.ungelesene_absender = [f"{m.from_addr} ({m.folder})" for m in alle_mails]
        relevante = [m for m in alle_mails if _is_job_alert_sender(m.from_addr)]
        result.emails_gefunden = len(relevante)

        for mail in relevante:
            if db.job_alert_mail_processed(mail.message_id):
                # Bereits ausgewertet, aber das \Seen-Flag konnte serverseitig
                # nicht gesetzt werden (z.B. READ-ONLY-Ordner wie Web.de's
                # "Unbekannt") - ohne diesen Check wuerde Claude die gleiche
                # Mail bei jedem Durchlauf erneut kostenpflichtig auswerten.
                continue

            inhalt = mail.html or mail.body
            inhalt = _clean_html(inhalt) if mail.html else inhalt[:_MAX_CONTENT_CHARS]
            try:
                jobs = extract_jobs_from_email(api_key, mail.subject, inhalt, model)
            except JobAlertImportError as exc:
                result.fehler.append(f"'{mail.subject}': {exc}")
                continue

            result.emails_verarbeitet += 1
            for job in jobs:
                titel = str(job.get("titel", "")).strip()
                if not titel:
                    continue
                firma = str(job.get("firma", "")).strip()
                ort = str(job.get("ort", "")).strip()
                url = str(job.get("url", "")).strip()
                beschreibung = str(job.get("beschreibung", "")).strip()

                refnr = _make_refnr(url, titel, firma)
                if db.job_exists(refnr):
                    continue

                score = matching.score_job(profile, titel, beschreibung or titel)
                if score < profile.match_threshold:
                    continue

                db.insert_job(
                    refnr=refnr,
                    titel=titel,
                    firma=firma,
                    ort=ort,
                    url=url,
                    beschreibung=beschreibung,
                    veroeffentlicht_am=now_iso,
                    match_score=score,
                )
                result.jobs_neu += 1

            db.mark_job_alert_mail_processed(mail.message_id)
            try:
                client.mark_seen(mail.uid, mail.folder)
            except ImapError as exc:
                result.fehler.append(
                    f"'{mail.subject}': ausgewertet, aber im Postfach nicht als gelesen "
                    f"markierbar ({exc}). Wird dank interner Verlaufsverfolgung trotzdem "
                    "nicht erneut verarbeitet."
                )

    return result
