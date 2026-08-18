"""Lokales, regelbasiertes Match-Scoring zwischen Nutzerprofil und Stellenanzeige.

1:1 portiert aus der Desktop-App (siehe dortiges core/matching.py fuer die
ausfuehrliche Begruendung des "weichen" Teilwort-Matchings). Einziger
Unterschied: das Profil liegt hier als SQLAlchemy-Objekt mit JSON-Spalten
vor statt als Dataclass, Berufserfahrung/Ausbildung sind daher Listen von
dicts statt von Dataclass-Instanzen.
"""
from __future__ import annotations

import re

from app.models.profile import ProfileData

_WUNSCHJOBTITEL_WEIGHT = (6, 2)
_SKILL_WEIGHT = (3, 3)
_ERFAHRUNG_WEIGHT = (2, 2)
_AUSBILDUNG_WEIGHT = (1, 1)

_MIN_WORD_LENGTH = 3
_STOPWORDS = {"und", "der", "die", "das", "fuer", "mit", "bei", "von", "the", "and", "for"}

_WORD_SPLIT_PATTERN = re.compile(r"[^a-zA-ZäöüÄÖÜß0-9+#.]+")


def _term_words(term: str) -> list[str]:
    words = _WORD_SPLIT_PATTERN.split((term or "").lower())
    return [w for w in words if len(w) >= _MIN_WORD_LENGTH and w not in _STOPWORDS]


def _match_fraction(text: str, term: str) -> float:
    words = _term_words(term)
    if not words:
        return 0.0
    matched = sum(1 for w in words if w in text)
    return matched / len(words)


def score_job(profile: ProfileData, titel: str, beschreibung: str) -> int:
    titel_l = (titel or "").lower()
    beschreibung_l = (beschreibung or "").lower()

    terms: list[tuple[str, tuple[int, int]]] = []
    terms += [(t, _WUNSCHJOBTITEL_WEIGHT) for t in (profile.wunschjobtitel or [])]
    terms += [(s, _SKILL_WEIGHT) for s in (profile.skills or [])]
    terms += [
        (e.get("position", ""), _ERFAHRUNG_WEIGHT)
        for e in (profile.berufserfahrung or [])
        if e.get("position")
    ]
    terms += [
        (a.get("abschluss", ""), _AUSBILDUNG_WEIGHT)
        for a in (profile.ausbildung or [])
        if a.get("abschluss")
    ]

    if not terms:
        return 0

    max_possible = 0
    raw_score = 0.0
    for term, (titel_weight, beschreibung_weight) in terms:
        max_possible += titel_weight + beschreibung_weight
        raw_score += titel_weight * _match_fraction(titel_l, term)
        raw_score += beschreibung_weight * _match_fraction(beschreibung_l, term)

    if max_possible == 0:
        return 0
    return round(100 * raw_score / max_possible)
