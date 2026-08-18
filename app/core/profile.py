"""Profilverwaltung: mehrere Nutzer, eigenes Profil, eigene Zugangsdaten.

Nicht-sensible Profildaten (Qualifikationen, Erfahrungen, Skills, ...) liegen
als Klartext-JSON pro Profil. Zugangsdaten (E-Mail-Konto, API-Keys) landen
ausschliesslich verschluesselt im Vault (siehe crypto.py) und nie im Code
oder in einer geteilten Konfigurationsdatei.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from app.config import (
    DEFAULT_MATCH_THRESHOLD,
    PROFILES_DIR,
    REGISTRY_FILE,
    ensure_app_dirs,
    profile_dir,
    profile_meta_path,
    vault_path,
)
from app.core.crypto import Vault, WrongPasswordError

__all__ = ["Profile", "ProfileRegistryEntry", "WrongPasswordError", "ProfileManager"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "profil"


@dataclass
class Erfahrung:
    firma: str = ""
    position: str = ""
    zeitraum: str = ""
    beschreibung: str = ""


@dataclass
class Ausbildung:
    institution: str = ""
    abschluss: str = ""
    zeitraum: str = ""


@dataclass
class Sprache:
    sprache: str = ""
    niveau: str = ""


@dataclass
class Profile:
    slug: str
    display_name: str
    created_at: str = field(default_factory=_now_iso)

    # Persoenliche Angaben (fuer Anschreiben-Absenderblock)
    name: str = ""
    adresse: str = ""
    telefon: str = ""
    email: str = ""

    # Wunschposition
    wunschjobtitel: list[str] = field(default_factory=list)
    wunschort: str = ""
    umkreis_km: int = 25
    arbeitszeit: str = "vz"  # vz/tz/snw/ho/mj gemaess BA-API

    # Qualifikationsprofil
    berufserfahrung: list[Erfahrung] = field(default_factory=list)
    ausbildung: list[Ausbildung] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    sprachen: list[Sprache] = field(default_factory=list)
    zertifikate: list[str] = field(default_factory=list)

    # Anlagen (z.B. Zeugnisse), Dateinamen unter config.anlagen_dir(slug) -
    # werden automatisch an jede versendete Bewerbung mitangehaengt.
    anlagen: list[str] = field(default_factory=list)

    # Anpassbare Zusatzanweisungen fuer die Anschreiben-Generierung (siehe
    # core/cover_letter.py)
    cover_letter_hinweise: str = ""

    # Einstellungen
    match_threshold: int = DEFAULT_MATCH_THRESHOLD
    auto_send_enabled: bool = False  # Vorschau-Modus ist Standard (Versand deaktiviert)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        data = dict(data)
        data["berufserfahrung"] = [Erfahrung(**e) for e in data.get("berufserfahrung", [])]
        data["ausbildung"] = [Ausbildung(**a) for a in data.get("ausbildung", [])]
        data["sprachen"] = [Sprache(**s) for s in data.get("sprachen", [])]
        return cls(**data)


@dataclass
class ProfileRegistryEntry:
    slug: str
    display_name: str
    created_at: str


class ProfileManager:
    """Verwaltet Profil-Registry, Anlage, Login und Speicherung."""

    def __init__(self) -> None:
        ensure_app_dirs()
        if not REGISTRY_FILE.exists():
            REGISTRY_FILE.write_text(json.dumps([]), encoding="utf-8")

    def list_profiles(self) -> list[ProfileRegistryEntry]:
        raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        return [ProfileRegistryEntry(**entry) for entry in raw]

    def _save_registry(self, entries: list[ProfileRegistryEntry]) -> None:
        REGISTRY_FILE.write_text(
            json.dumps([asdict(e) for e in entries], indent=2), encoding="utf-8"
        )

    def _unique_slug(self, display_name: str) -> str:
        base = _slugify(display_name)
        existing = {e.slug for e in self.list_profiles()}
        slug = base
        counter = 2
        while slug in existing:
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def create_profile(self, display_name: str, master_password: str) -> tuple[Profile, Vault]:
        slug = self._unique_slug(display_name)
        profile = Profile(slug=slug, display_name=display_name, name=display_name)
        profile_dir(slug).mkdir(parents=True, exist_ok=True)
        profile_meta_path(slug).write_text(
            json.dumps(profile.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        vault = Vault.create(vault_path(slug), master_password)

        entries = self.list_profiles()
        entries.append(
            ProfileRegistryEntry(slug=slug, display_name=display_name, created_at=profile.created_at)
        )
        self._save_registry(entries)
        return profile, vault

    def login(self, slug: str, master_password: str) -> tuple[Profile, Vault]:
        vault = Vault.load(vault_path(slug), master_password)  # wirft WrongPasswordError
        data = json.loads(profile_meta_path(slug).read_text(encoding="utf-8"))
        profile = Profile.from_dict(data)
        return profile, vault

    def save_profile(self, profile: Profile) -> None:
        profile_meta_path(profile.slug).write_text(
            json.dumps(profile.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def delete_profile(self, slug: str) -> None:
        shutil.rmtree(profile_dir(slug), ignore_errors=True)
        entries = [e for e in self.list_profiles() if e.slug != slug]
        self._save_registry(entries)
