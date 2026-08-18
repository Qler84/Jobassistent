"""Zentrale Konfiguration - alles aus Umgebungsvariablen, nichts hartcodiert.

Lokale Entwicklung liest zusaetzlich eine .env-Datei (siehe .env.example).
Auf Render werden die Werte als Umgebungsvariablen im Dashboard gesetzt
(siehe render.yaml).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Datenbank (externe Postgres-Instanz, z.B. Neon oder Supabase - siehe README)
    database_url: str

    # Ein einziges Geheimnis, aus dem sowohl der JWT-Signierschluessel als auch
    # der Verschluesselungsschluessel fuer abgelegte Zugangsdaten abgeleitet
    # werden (siehe security.py) - unterschiedliche Ableitungskontexte trennen
    # die beiden Verwendungszwecke, sodass ein Leak des einen nicht automatisch
    # den anderen kompromittiert.
    app_secret_key: str

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 Tage

    # Kommagetrennte Liste erlaubter Frontend-Origins fuer CORS
    cors_origins: str = "http://localhost:5173"

    default_claude_model: str = "claude-sonnet-5"
    default_match_threshold: int = 20

    # BA Jobsuche-API (community-dokumentiert, oeffentlicher Key ohne
    # Registrierung - siehe github.com/bundesAPI/jobsuche-api)
    ba_api_base_url: str = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/"
    ba_api_key: str = "jobboerse-jobsuche"

    # Groessenlimits fuer Datei-Uploads (in DB als bytea gespeichert, siehe
    # models/attachment.py - kein separater Objektspeicher auf dem kostenlosen
    # Render-Tier noetig, Dateien sind klein genug fuer Zeugnisse/Lebenslaeufe)
    max_attachment_bytes: int = 8 * 1024 * 1024
    max_profile_import_bytes: int = 32 * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
