"""Profil-Import aus Lebenslauf/Zeugnis-PDFs via Claude.

Claude liest die PDFs direkt (native PDF-Unterstuetzung der Messages API,
kein Beta-Header noetig) und extrahiert strukturierte Profildaten. Das
Ergebnis wird dem Nutzer nur als Vorschlag ins Profil-Formular eingetragen -
gespeichert wird erst nach manueller Pruefung und Klick auf 'Profil
speichern' (siehe ui/profile_editor.py).
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import anthropic

from app.config import DEFAULT_CLAUDE_MODEL

# Anthropic-Limit fuer PDF-Dokumente in einem Request (32 MB, max. 600 Seiten).
_MAX_TOTAL_BYTES = 32 * 1024 * 1024


class ProfileImportError(Exception):
    pass


_EXTRACTION_PROMPT = """Du analysierst Lebenslauf- und Zeugnis-Dokumente und extrahierst daraus
strukturierte Profildaten fuer eine Jobsuche-App. Nutze ausschliesslich Informationen, die
tatsaechlich in den Dokumenten stehen - erfinde nichts.

Antworte AUSSCHLIESSLICH mit einem einzigen JSON-Objekt (keine Erklaerungen, kein Markdown,
keine Codebloecke), exakt in diesem Format:

{
  "name": "Vor- und Nachname",
  "adresse": "Strasse Hausnummer, PLZ Ort",
  "telefon": "Telefonnummer, falls vorhanden, sonst leerer String",
  "email": "E-Mail-Adresse, falls vorhanden, sonst leerer String",
  "wunschjobtitel": ["Jobtitel1", "Jobtitel2"],
  "berufserfahrung": [
    {"firma": "...", "position": "...", "zeitraum": "...", "beschreibung": "..."}
  ],
  "ausbildung": [
    {"institution": "...", "abschluss": "...", "zeitraum": "..."}
  ],
  "skills": ["Skill1", "Skill2"],
  "sprachen": [{"sprache": "...", "niveau": "..."}],
  "zertifikate": ["Zertifikat1"]
}

Felder ohne Information: leere Liste bzw. leerer String, nicht weglassen. "wunschjobtitel"
leitest du aus der zuletzt ausgeuebten bzw. angestrebten Position ab."""


def _encode_pdf(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "type": "document",
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64.standard_b64encode(data).decode("utf-8"),
        },
    }


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
    if not match:
        raise ProfileImportError("Claude hat kein verwertbares JSON zurueckgegeben.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ProfileImportError(f"Antwort von Claude war kein gueltiges JSON: {exc}") from exc


def extract_profile_from_documents(
    api_key: str, pdf_paths: list[Path], model: str = DEFAULT_CLAUDE_MODEL
) -> dict:
    """Liest Lebenslauf/Zeugnis-PDFs und liefert einen Vorschlag fuer die
    Profildaten als dict. Dient nur zur Vorausfuellung des Profil-Formulars -
    der Nutzer prueft und speichert selbst."""
    if not api_key:
        raise ProfileImportError("Kein Anthropic-API-Key im Profil hinterlegt.")
    if not pdf_paths:
        raise ProfileImportError("Keine PDF-Dateien ausgewaehlt.")

    total_size = sum(p.stat().st_size for p in pdf_paths)
    if total_size > _MAX_TOTAL_BYTES:
        raise ProfileImportError(
            "Die ausgewaehlten PDFs sind zusammen groesser als 32 MB - bitte weniger oder "
            "kleinere Dateien auswaehlen."
        )

    content = [_encode_pdf(p) for p in pdf_paths]
    content.append({"type": "text", "text": _EXTRACTION_PROMPT})

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.APIError as exc:
        raise ProfileImportError(f"Claude-API-Fehler: {exc}") from exc

    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(text)
