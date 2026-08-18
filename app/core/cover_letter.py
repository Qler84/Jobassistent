"""Anschreiben-Generierung via Anthropic Claude API.

Wird ausschliesslich nach expliziter Bestaetigung einer Stellenanzeige durch
den Nutzer aufgerufen (siehe ui/suggestions_view.py) - nie automatisch im
Hintergrund. Nutzt den vom Nutzer im eigenen Profil hinterlegten API-Key.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import anthropic

from app.config import DEFAULT_CLAUDE_MODEL
from app.core.profile import Profile

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_RESPONSE_PATTERN = re.compile(
    r"ERKANNTER_ANSPRECHPARTNER:\s*(.*?)\s*\n-{3}BRIEF-{3}\s*\n(.*)", re.DOTALL
)


class CoverLetterError(Exception):
    pass


@dataclass
class CoverLetterResult:
    text: str
    erkannter_ansprechpartner: str | None


def extract_contact_email(stellentext: str) -> str | None:
    """Sucht die erste E-Mail-Adresse im Stellentext (heuristische Ansprechpartner-Erkennung)."""
    match = _EMAIL_PATTERN.search(stellentext or "")
    return match.group(0) if match else None


def _profile_summary(profile: Profile) -> str:
    lines = [f"Name: {profile.name}"]
    if profile.skills:
        lines.append("Skills: " + ", ".join(profile.skills))
    if profile.berufserfahrung:
        lines.append("Berufserfahrung:")
        for e in profile.berufserfahrung:
            lines.append(f"  - {e.position} bei {e.firma} ({e.zeitraum}): {e.beschreibung}")
    if profile.ausbildung:
        lines.append("Ausbildung:")
        for a in profile.ausbildung:
            lines.append(f"  - {a.abschluss}, {a.institution} ({a.zeitraum})")
    if profile.sprachen:
        lines.append(
            "Sprachen: " + ", ".join(f"{s.sprache} ({s.niveau})" for s in profile.sprachen)
        )
    if profile.zertifikate:
        lines.append("Zertifikate: " + ", ".join(profile.zertifikate))
    return "\n".join(lines)


def _anrede_anweisung(ansprechpartner: str | None) -> str:
    if ansprechpartner:
        return (
            f'Nutze als Anrede "Sehr geehrte(r) {ansprechpartner}," und gib in der ersten Zeile '
            f'deiner Antwort exakt "ERKANNTER_ANSPRECHPARTNER: {ansprechpartner}" aus.'
        )
    return (
        "Pruefe zunaechst, ob in der Stellenanzeige unten ein/e persoenliche/r Ansprechpartner/in "
        'namentlich genannt wird (z.B. "Bei Fragen wenden Sie sich an Frau Schmidt", eine '
        "Kontaktperson im Anzeigentext o.ae. - keine allgemeinen Firmennamen). Falls ja, gib den "
        'Namen in der ersten Zeile deiner Antwort als "ERKANNTER_ANSPRECHPARTNER: <Name>" aus und '
        'nutze in der Anrede "Sehr geehrte(r) Herr/Frau <Nachname>,". Falls kein Name erkennbar '
        'ist, gib "ERKANNTER_ANSPRECHPARTNER: " (danach nichts) aus und nutze "Sehr geehrte Damen '
        'und Herren,".'
    )


def _parse_response(raw: str) -> CoverLetterResult:
    match = _RESPONSE_PATTERN.match(raw.strip())
    if not match:
        # Claude hat sich nicht an das Antwortformat gehalten - kompletten Text als Brief
        # verwenden, statt einen Fehler zu werfen.
        return CoverLetterResult(text=raw.strip(), erkannter_ansprechpartner=None)
    name = match.group(1).strip() or None
    text = match.group(2).strip()
    return CoverLetterResult(text=text, erkannter_ansprechpartner=name)


def generate_cover_letter(
    profile: Profile,
    api_key: str,
    job_titel: str,
    arbeitgeber: str,
    ort: str,
    beschreibung: str,
    ansprechpartner: str | None = None,
    model: str = DEFAULT_CLAUDE_MODEL,
) -> CoverLetterResult:
    """Generiert das Anschreiben und liefert zusaetzlich den von Claude aus der
    Stellenanzeige erkannten Ansprechpartner-Namen zurueck (falls vorhanden),
    damit die UI das Namensfeld automatisch vorausfuellen kann - der Nutzer
    sieht das Ergebnis immer und kann es vor der Freigabe korrigieren."""
    if not api_key:
        raise CoverLetterError("Kein Anthropic-API-Key im Profil hinterlegt.")

    zusatz = ""
    if profile.cover_letter_hinweise.strip():
        zusatz = f"""

ZUSAETZLICHE ANWEISUNGEN DES NUTZERS (unbedingt beruecksichtigen, haben Vorrang vor den
allgemeinen Stilvorgaben unten, sofern sie ihnen widersprechen):
{profile.cover_letter_hinweise.strip()}"""

    prompt = f"""Du hilfst dabei, ein individuelles, professionelles deutsches Bewerbungsanschreiben zu formulieren.

BEWERBERPROFIL:
{_profile_summary(profile)}

STELLENANZEIGE:
Titel: {job_titel}
Unternehmen: {arbeitgeber}
Ort: {ort}
Beschreibung:
{beschreibung}

AUFGABE:
Schreibe ein Bewerbungsanschreiben auf Deutsch (ca. 250-350 Woerter), das konkret auf die
Anforderungen dieser Stellenanzeige eingeht und die passendsten Qualifikationen/Erfahrungen
des Bewerberprofils hervorhebt. Ton: professionell, selbstbewusst, nicht floskelhaft, keine
Übertreibungen oder erfundenen Fakten - nutze ausschliesslich die im Profil genannten Angaben.
{_anrede_anweisung(ansprechpartner)}
Schliesse mit einer Grussformel und dem Namen "{profile.name}". Gib ausschliesslich den
Brieftext zurueck, ohne zusaetzliche Erklaerungen, ohne Betreffzeile, ohne Adressblock.{zusatz}

ANTWORTFORMAT (exakt einhalten):
ERKANNTER_ANSPRECHPARTNER: <Name oder leer>
---BRIEF---
<Der Brieftext gemaess obiger Vorgaben, sonst nichts>"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        raise CoverLetterError(f"Claude-API-Fehler: {exc}") from exc

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    return _parse_response(raw)
