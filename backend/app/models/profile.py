"""Nicht-sensible Profildaten (Qualifikationen, Wunschposition, ...).

Listen/verschachtelte Strukturen (Berufserfahrung, Ausbildung, Sprachen)
liegen als JSON-Spalten - analog zum Klartext-JSON-Profil der Desktop-App,
hier aber pro Nutzer in Postgres statt einer lokalen Datei.
"""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProfileData(Base):
    __tablename__ = "profile_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    name: Mapped[str] = mapped_column(String(255), default="")
    adresse: Mapped[str] = mapped_column(String(500), default="")
    telefon: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(255), default="")

    wunschjobtitel: Mapped[list] = mapped_column(JSON, default=list)
    wunschort: Mapped[str] = mapped_column(String(255), default="")
    umkreis_km: Mapped[int] = mapped_column(Integer, default=25)
    arbeitszeit: Mapped[str] = mapped_column(String(20), default="vz")

    berufserfahrung: Mapped[list] = mapped_column(JSON, default=list)
    ausbildung: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    sprachen: Mapped[list] = mapped_column(JSON, default=list)
    zertifikate: Mapped[list] = mapped_column(JSON, default=list)

    cover_letter_hinweise: Mapped[str] = mapped_column(Text, default="")

    match_threshold: Mapped[int] = mapped_column(Integer, default=20)
    auto_send_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="profile")
