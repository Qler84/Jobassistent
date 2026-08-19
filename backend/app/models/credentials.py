"""Zugangsdaten pro Nutzer - sensible Felder werden ausschliesslich
verschluesselt gespeichert (siehe security.py: encrypt_secret/decrypt_secret),
nie im Klartext in der DB."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserCredentials(Base):
    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imap_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # E-Mail-Adresse + Passwort gelten fuer SMTP und IMAP gleichermassen
    # (ein E-Mail-Konto, siehe main_window.py der Desktop-App).
    email_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_password_enc: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Der Anthropic-API-Key ist global (siehe config.py) - kein Pro-Nutzer-Feld.
    claude_model: Mapped[str] = mapped_column(String(100), default="claude-sonnet-5")

    imap_auto_check_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    imap_auto_check_minutes: Mapped[int] = mapped_column(Integer, default=30)

    user = relationship("User", back_populates="credentials")
