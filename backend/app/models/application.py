from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# status-Werte: entwurf, freigegeben, versendet, antwort_erhalten, einladung,
# absage, keine_rueckmeldung (identisch zur Desktop-App)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))

    anschreiben_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    betreff: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kontakt_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ansprechpartner: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="entwurf")
    status_quelle: Mapped[str] = mapped_column(String(20), default="manuell")  # auto/manuell

    erstellt_am: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    versendet_am: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)

    job = relationship("Job", back_populates="applications")
