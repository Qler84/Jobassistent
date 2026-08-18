"""Verhindert doppelte, kostenpflichtige Claude-Auswertung derselben
Job-Alert-Mail, unabhaengig vom IMAP-\\Seen-Flag (das bei manchen
Postfach-Ordnern serverseitig nicht gesetzt werden kann - siehe
core/email_imap.py)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProcessedJobAlertMail(Base):
    __tablename__ = "processed_job_alert_mails"
    __table_args__ = (UniqueConstraint("user_id", "message_id", name="uq_processed_mail_user_msgid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[str] = mapped_column(String(500), nullable=False)
    verarbeitet_am: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
