"""Master-Passwort-basierte Verschluesselung fuer Zugangsdaten pro Profil.

Jedes Profil hat sein eigenes Master-Passwort. Daraus wird via PBKDF2 ein
symmetrischer Schluessel abgeleitet, mit dem ein Fernet-Vault (AES) ver- und
entschluesselt wird. Das Master-Passwort selbst wird nie gespeichert -
lediglich ein verschluesselter Canary-Wert dient zur Verifikation beim Login.
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import PBKDF2_ITERATIONS

CANARY_VALUE = "jobassistant-vault-ok"


class WrongPasswordError(Exception):
    """Master-Passwort stimmt nicht mit dem gespeicherten Vault ueberein."""


def _derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    raw_key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


@dataclass
class Vault:
    """Haelt die im Klartext entschluesselten Secrets eines Profils im RAM."""

    path: Path
    salt: bytes
    fernet: Fernet
    secrets: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, path: Path, master_password: str) -> "Vault":
        salt = os.urandom(16)
        key = _derive_key(master_password, salt)
        fernet = Fernet(key)
        vault = cls(path=path, salt=salt, fernet=fernet, secrets={})
        vault.save()
        return vault

    @classmethod
    def load(cls, path: Path, master_password: str) -> "Vault":
        raw = json.loads(path.read_text(encoding="utf-8"))
        salt = base64.b64decode(raw["salt"])
        key = _derive_key(master_password, salt)
        fernet = Fernet(key)
        try:
            payload = fernet.decrypt(raw["payload"].encode("utf-8"))
        except InvalidToken as exc:
            raise WrongPasswordError("Master-Passwort ist falsch.") from exc
        data = json.loads(payload.decode("utf-8"))
        if data.get("_canary") != CANARY_VALUE:
            raise WrongPasswordError("Master-Passwort ist falsch.")
        secrets = data.get("secrets", {})
        return cls(path=path, salt=salt, fernet=fernet, secrets=secrets)

    def save(self) -> None:
        payload = json.dumps({"_canary": CANARY_VALUE, "secrets": self.secrets}).encode("utf-8")
        encrypted = self.fernet.encrypt(payload)
        raw = {
            "salt": base64.b64encode(self.salt).decode("utf-8"),
            "payload": encrypted.decode("utf-8"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(raw), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self.secrets.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.secrets[key] = value

    def change_master_password(self, new_master_password: str) -> None:
        new_salt = os.urandom(16)
        self.salt = new_salt
        self.fernet = Fernet(_derive_key(new_master_password, new_salt))
        self.save()
