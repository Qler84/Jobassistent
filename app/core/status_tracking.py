"""Verknuepft IMAP-Postfachpruefung mit der Bewerbungs-Datenbank.

Zuordnungsstrategie einer eingehenden Mail zu einer Bewerbung:
1. Message-ID-Abgleich ueber In-Reply-To/References (zuverlaessig, sofern
   beim Versand eine Message-ID gespeichert wurde, siehe email_smtp.py).
2. Fallback: Absenderadresse == hinterlegte Kontakt-E-Mail einer bereits
   versendeten Bewerbung.
Nicht zuordenbare Mails werden ignoriert und bleiben ungelesen - es wird
nie das gesamte Postfach pauschal als gelesen markiert.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.database import Application, Database
from app.core.email_imap import ImapClient, ImapConfig, ImapError, classify_reply


@dataclass
class StatusUpdate:
    application_id: int
    job_id: int
    von_status: str
    neuer_status: str
    absender: str
    betreff: str


def _find_matching_application(db: Database, mail) -> Application | None:
    candidate_ids = list(mail.reference_ids)
    if mail.message_id:
        candidate_ids.append(mail.message_id)
    application = db.find_application_by_message_id(candidate_ids) if candidate_ids else None
    if application is not None:
        return application

    if mail.from_addr:
        candidates = db.find_applications_by_contact_email(mail.from_addr)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return max(candidates, key=lambda a: a.versendet_am or "")
    return None


def run_imap_check(config: ImapConfig, db: Database) -> list[StatusUpdate]:
    """Prueft ungelesene Mails, ordnet sie bekannten Bewerbungen zu und
    aktualisiert deren Status. Wirft ImapError bei Verbindungsproblemen."""
    updates: list[StatusUpdate] = []
    with ImapClient(config) as client:
        for mail in client.fetch_unseen():
            application = _find_matching_application(db, mail)
            if application is None:
                continue

            neuer_status = classify_reply(mail.subject, mail.body)
            von_status = application.status
            db.update_application(application.id, status=neuer_status, status_quelle="auto")
            try:
                client.mark_seen(mail.uid, mail.folder)
            except ImapError:
                # Manche Ordner (z.B. Web.de's virtuelle "Unbekannt"-Kategorie)
                # sind serverseitig READ-ONLY - Status wurde trotzdem korrekt
                # uebernommen, nur das Postfach-Flag bleibt unveraendert.
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
