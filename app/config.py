"""Zentrale Pfad- und Konstantenverwaltung.

Nutzerdaten (Profile, Vaults, Datenbanken, generierte PDFs) liegen bewusst
ausserhalb des Projekt-/Code-Ordners unter %APPDATA%, damit nie persoenliche
Daten im Repository landen und mehrere Profile sauber getrennt sind.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "JobAssistant"


def resource_path(relative: str) -> Path:
    """Pfad zu einer mitgelieferten Ressource (z.B. Icon) - funktioniert sowohl
    beim Start aus dem Quellcode als auch aus der von PyInstaller gepackten
    .exe (dort liegen die Dateien in einem temporaeren Entpackverzeichnis,
    das PyInstaller in sys._MEIPASS hinterlegt)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


ICON_PATH = resource_path("assets/icon.ico")


def _app_data_root() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    # Fallback fuer Nicht-Windows-Systeme (z.B. Entwicklung/Tests auf macOS/Linux)
    return Path.home() / f".{APP_NAME.lower()}"


APP_DATA_DIR = _app_data_root()
PROFILES_DIR = APP_DATA_DIR / "profiles"
REGISTRY_FILE = APP_DATA_DIR / "profile_registry.json"

# BA Jobsuche-API (community-dokumentiert, siehe github.com/bundesAPI/jobsuche-api)
BA_API_BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/"
BA_API_KEY = "jobboerse-jobsuche"

DEFAULT_MATCH_THRESHOLD = 20
DEFAULT_CLAUDE_MODEL = "claude-sonnet-5"

PBKDF2_ITERATIONS = 480_000


def ensure_app_dirs() -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def profile_dir(slug: str) -> Path:
    return PROFILES_DIR / slug


def vault_path(slug: str) -> Path:
    return profile_dir(slug) / "vault.enc"


def db_path(slug: str) -> Path:
    return profile_dir(slug) / "jobs.db"


def profile_meta_path(slug: str) -> Path:
    return profile_dir(slug) / "profile.json"


def cover_letters_dir(slug: str) -> Path:
    path = profile_dir(slug) / "anschreiben"
    path.mkdir(parents=True, exist_ok=True)
    return path


def anlagen_dir(slug: str) -> Path:
    path = profile_dir(slug) / "anlagen"
    path.mkdir(parents=True, exist_ok=True)
    return path


# UI-Einstellungen (z.B. Hell-/Dunkelmodus) gelten pro Installation, nicht pro
# Profil - unverschluesselt, da keine sensiblen Daten, und schon vor dem Login
# gebraucht (Login-Fenster soll auch das gewaehlte Theme nutzen).
UI_SETTINGS_PATH = APP_DATA_DIR / "ui_settings.json"


def load_ui_settings() -> dict:
    ensure_app_dirs()
    if not UI_SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(UI_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_ui_settings(settings: dict) -> None:
    ensure_app_dirs()
    UI_SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
