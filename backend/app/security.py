"""Passwort-Hashing, JWT-Sessions und Verschluesselung abgelegter Zugangsdaten.

Sicherheitsmodell-Unterschied zur Desktop-App: dort konnte niemand außer dem
Nutzer selbst (mit seinem Master-Passwort im RAM) die Zugangsdaten
entschluesseln - nicht einmal der Entwickler. Ein zustandsloser Web-Server
kann dieses "Zero-Knowledge"-Modell nicht sinnvoll abbilden (jeder Request
braucht Zugriff auf SMTP/IMAP/API-Key, ohne dass der Nutzer sein Passwort bei
jeder Aktion erneut eingibt). Stattdessen: normales Login per Passwort-Hash,
und serverseitige Verschluesselung der Zugangsdaten "at rest" mit einem
Schluessel aus APP_SECRET_KEY (schuetzt bei DB-Diebstahl, nicht vor dem
Server-Betreiber selbst - siehe README fuer die volle Erklaerung).
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

settings = get_settings()


def _derive_key(context: str) -> bytes:
    digest = hashlib.sha256(f"{settings.app_secret_key}:{context}".encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_JWT_SECRET = settings.app_secret_key
_FERNET = Fernet(_derive_key("secrets-at-rest"))


# --- Passwort-Hashing --------------------------------------------------

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# --- JWT-Sessions --------------------------------------------------------

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, _JWT_SECRET, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


# --- Verschluesselung von Zugangsdaten (SMTP/IMAP-Passwort, API-Key) -----

def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _FERNET.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _FERNET.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
