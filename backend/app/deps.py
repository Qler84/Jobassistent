"""Gemeinsame FastAPI-Dependencies: DB-Session und eingeloggter Nutzer."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet.")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sitzung ungueltig oder abgelaufen.")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nutzer nicht gefunden.")
    return user
