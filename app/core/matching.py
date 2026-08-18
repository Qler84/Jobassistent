"""Lokales, regelbasiertes Match-Scoring zwischen Nutzerprofil und Stellenanzeige.

Laeuft komplett offline (kein API-Call), damit auch bei vielen Treffern
schnell und kostenlos vorgefiltert werden kann (Qualitaet vor Quantitaet:
siehe DEFAULT_MATCH_THRESHOLD in config.py).

Bewusst "weiches" Matching statt exaktem Phrasenvergleich: Stellentitel
unterscheiden sich haeufig nur in Kleinigkeiten vom Wunschjobtitel (z.B.
"Softwareentwickler (m/w/d)" vs. "Softwareentwickler:in" vs. "Software
Developer") - ein exakter Vergleich der ganzen Phrase wuerde hier oft 0%
liefern. Stattdessen wird pro Begriff (Skill, Wunschjobtitel, ...) geprueft,
wie viele seiner einzelnen Woerter im Jobtext vorkommen, und anteilig
gewertet.
"""
from __future__ import annotations

import re

from app.core.profile import Profile

# (Gewicht im Titel, Gewicht in der Beschreibung)
_WUNSCHJOBTITEL_WEIGHT = (6, 2)
_SKILL_WEIGHT = (3, 3)
_ERFAHRUNG_WEIGHT = (2, 2)
_AUSBILDUNG_WEIGHT = (1, 1)

# Woerter unter dieser Laenge (Artikel, Praepositionen, "m/w/d" etc.) werden
# beim Aufteilen eines Begriffs in Einzelwoerter ignoriert.
_MIN_WORD_LENGTH = 3
_STOPWORDS = {"und", "der", "die", "das", "fuer", "mit", "bei", "von", "the", "and", "for"}

_WORD_SPLIT_PATTERN = re.compile(r"[^a-zA-ZäöüÄÖÜß0-9+#.]+")


def _term_words(term: str) -> list[str]:
    words = _WORD_SPLIT_PATTERN.split(term.lower())
    return [w for w in words if len(w) >= _MIN_WORD_LENGTH and w not in _STOPWORDS]


def _match_fraction(text: str, term: str) -> float:
    """Anteil der Woerter eines Begriffs, die (als Teilstring, um z.B.
    Deklinationen/Genderformen abzudecken) im Text vorkommen - 0.0 bis 1.0."""
    words = _term_words(term)
    if not words:
        return 0.0
    matched = sum(1 for w in words if w in text)
    return matched / len(words)


def score_job(profile: Profile, titel: str, beschreibung: str) -> int:
    """Liefert einen Match-Score von 0 bis 100.

    Gewichtete, anteilige Uebereinstimmung zwischen Profil-Skills/
    Wunschposition/Erfahrung/Ausbildung und Jobtitel+Beschreibung. Exakte
    Skill- und Wunschjobtitel-Treffer zaehlen staerker als generische
    Ueberschneidungen, aber auch Teiltreffer (z.B. nur ein Wort eines
    mehrteiligen Jobtitels) geben anteilig Punkte statt leer auszugehen.
    """
    titel_l = (titel or "").lower()
    beschreibung_l = (beschreibung or "").lower()

    terms: list[tuple[str, tuple[int, int]]] = []
    terms += [(t, _WUNSCHJOBTITEL_WEIGHT) for t in profile.wunschjobtitel]
    terms += [(s, _SKILL_WEIGHT) for s in profile.skills]
    terms += [(e.position, _ERFAHRUNG_WEIGHT) for e in profile.berufserfahrung if e.position]
    terms += [(a.abschluss, _AUSBILDUNG_WEIGHT) for a in profile.ausbildung if a.abschluss]

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
