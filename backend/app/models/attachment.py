"""Vom Nutzer hinterlegte Anlagen (Lebenslauf, Zeugnisse), werden automatisch
an jede versendete Bewerbung angehaengt. Inhalt liegt direkt als Binaerdaten
in Postgres - auf dem kostenlosen Render-Tier ist die Festplatte des
Web-Service fluechtig (geht bei jedem Neustart verloren), ein externer
Objektspeicher waere fuer diese kleinen PDF-Dateien unnoetiger Overhead."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
