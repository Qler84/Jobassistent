from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("user_id", "refnr", name="uq_job_user_refnr"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    refnr: Mapped[str] = mapped_column(String(255), nullable=False)
    titel: Mapped[str] = mapped_column(String(500), default="")
    firma: Mapped[str] = mapped_column(String(500), default="")
    ort: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    veroeffentlicht_am: Mapped[str] = mapped_column(String(100), default="")
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="neu")  # neu/bestaetigt/abgelehnt
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
