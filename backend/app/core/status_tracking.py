"""Verknuepft IMAP-Postfachpruefung mit der Bewerbungs-Datenbank.

Zuordnungsstrategie (unveraendert aus der Desktop-App):
1. Message-ID-Abgleich ueber In-Reply-To/References.
2. Fallback: Absenderadresse == hinterlegte Kontakt-E-Mail einer bereits
   versendeten Bewerbung.
Nicht zuordenbare Mails werden ignoriert und bleiben ungelesen."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.email_imap import ImapClient, ImapConfig, ImapError, ParsedEmail, classify_reply
from app.models.application import Application


@dataclass
class StatusUpdate:
    application_id: int
    job_id: int
    von_status: str
    neuer_status: str
    absender: str
    betreff: str


def _find_matching_application(db: Session, user_id: int, mail: ParsedEmail) -> Application | None:
    candidate_ids = list(mail.reference_ids)
    if mail.message_id:
        candidate_ids.append(mail.message_id)

    if candidate_ids:
        application = (
            db.query(Application)
            .filter(Application.user_id == user_id, Application.message_id.in_(candidate_ids))
            .first()
        )
        if application is not None:
            return application

    if mail.from_addr:
        candidates = (
            db.query(Application)
            .filter(
                Application.user_id == user_id,
                Application.kontakt_email == mail.from_addr,
                Application.status == "versendet",
            )
            .all()
        )
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return max(candidates, key=lambda a: a.versendet_am or datetime.min.replace(tzinfo=timezone.utc))
    return None


def run_imap_check(config: ImapConfig, db: Session, user_id: int) -> list[StatusUpdate]:
    updates: list[StatusUpdate] = []
    with ImapClient(config) as client:
        for mail in client.fetch_unseen():
            application = _find_matching_application(db, user_id, mail)
            if application is None:
                continue

            neuer_status = classify_reply(mail.subject, mail.body)
            von_status = application.status
            application.status = neuer_status
            application.status_quelle = "auto"
            db.commit()
            try:
                client.mark_seen(mail.uid, mail.folder)
            except ImapError:
                pass

            updates.append(
                StatusUpdate(
                    application_id=application.id,
                    job_id=application.job_id,
                    von_status=von_status,
                    neuer_status=neuer_status,
                    absender=mail.from_addr,
                    betreff=mail.subject,
                )
            )
    return updates
