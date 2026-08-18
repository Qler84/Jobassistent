"""SQLite-Datenbank pro Profil: gefundene Jobs und Bewerbungen.

Eine Datenbank pro Profil (siehe config.db_path), damit Nutzer strikt
getrennt sind. Dedup von Jobs erfolgt ueber die eindeutige refnr der BA-API.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    refnr TEXT UNIQUE NOT NULL,
    titel TEXT NOT NULL,
    firma TEXT,
    ort TEXT,
    url TEXT,
    beschreibung TEXT,
    veroeffentlicht_am TEXT,
    match_score INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'neu',
    first_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_job_alert_mails (
    message_id TEXT PRIMARY KEY,
    verarbeitet_am TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    anschreiben_text TEXT,
    pdf_pfad TEXT,
    kontakt_email TEXT,
    status TEXT NOT NULL DEFAULT 'entwurf',
    status_quelle TEXT NOT NULL DEFAULT 'manuell',
    erstellt_am TEXT NOT NULL,
    versendet_am TEXT,
    message_id TEXT
);
"""

# status-Werte fuer applications:
# entwurf, freigegeben, versendet, antwort_erhalten, einladung, absage, keine_rueckmeldung

# Spalten, die in bestehenden Datenbanken (vor Phase 2) noch fehlen koennen.
_MIGRATIONS: dict[str, str] = {
    "message_id": "ALTER TABLE applications ADD COLUMN message_id TEXT",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: int
    refnr: str
    titel: str
    firma: str
    ort: str
    url: str
    beschreibung: str
    veroeffentlicht_am: str
    match_score: int
    status: str
    first_seen: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Job":
        return cls(**{k: row[k] for k in row.keys()})


@dataclass
class Application:
    id: int
    job_id: int
    anschreiben_text: Optional[str]
    pdf_pfad: Optional[str]
    kontakt_email: Optional[str]
    status: str
    status_quelle: str
    erstellt_am: str
    versendet_am: Optional[str]
    message_id: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Application":
        return cls(**{k: row[k] for k in row.keys()})


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            existing_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(applications)")
            }
            for column, ddl in _MIGRATIONS.items():
                if column not in existing_columns:
                    conn.execute(ddl)

    # --- Jobs -----------------------------------------------------------

    def job_exists(self, refnr: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE refnr = ?", (refnr,)).fetchone()
            return row is not None

    def insert_job(
        self,
        refnr: str,
        titel: str,
        firma: str,
        ort: str,
        url: str,
        beschreibung: str,
        veroeffentlicht_am: str,
        match_score: int,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT OR IGNORE INTO jobs
                   (refnr, titel, firma, ort, url, beschreibung, veroeffentlicht_am, match_score, status, first_seen)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'neu', ?)""",
                (refnr, titel, firma, ort, url, beschreibung, veroeffentlicht_am, match_score, _now_iso()),
            )
            return cur.lastrowid

    def list_jobs(self, status: Optional[str] = None) -> list[Job]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC, first_seen DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY match_score DESC, first_seen DESC"
                ).fetchall()
            return [Job.from_row(r) for r in rows]

    def get_job(self, job_id: int) -> Optional[Job]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return Job.from_row(row) if row else None

    def set_job_status(self, job_id: int, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))

    # --- Job-Alert-Mail-Tracking --------------------------------------------
    # Unabhaengig vom IMAP-\Seen-Flag: manche Postfach-Ordner (z.B. Web.de's
    # virtuelle "Unbekannt"-Kategorie) sind serverseitig READ-ONLY, das Flag
    # kann dort also nicht gesetzt werden. Ohne dieses Tracking wuerde die
    # gleiche Mail bei jedem Durchlauf erneut per Claude ausgewertet.

    def job_alert_mail_processed(self, message_id: str) -> bool:
        if not message_id:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_job_alert_mails WHERE message_id = ?", (message_id,)
            ).fetchone()
            return row is not None

    def mark_job_alert_mail_processed(self, message_id: str) -> None:
        if not message_id:
            return
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_job_alert_mails (message_id, verarbeitet_am) "
                "VALUES (?, ?)",
                (message_id, _now_iso()),
            )

    # --- Applications -----------------------------------------------------

    def create_application(self, job_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO applications (job_id, status, status_quelle, erstellt_am)
                   VALUES (?, 'entwurf', 'manuell', ?)""",
                (job_id, _now_iso()),
            )
            return cur.lastrowid

    def get_application_for_job(self, job_id: int) -> Optional[Application]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM applications WHERE job_id = ? ORDER BY id DESC LIMIT 1", (job_id,)
            ).fetchone()
            return Application.from_row(row) if row else None

    def update_application(self, application_id: int, **fields) -> None:
        if not fields:
            return
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [application_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE applications SET {columns} WHERE id = ?", values)

    def list_applications(self, status: Optional[str] = None) -> list[Application]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM applications WHERE status = ? ORDER BY erstellt_am DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM applications ORDER BY erstellt_am DESC"
                ).fetchall()
            return [Application.from_row(r) for r in rows]

    def get_application(self, application_id: int) -> Optional[Application]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM applications WHERE id = ?", (application_id,)
            ).fetchone()
            return Application.from_row(row) if row else None

    def list_applications_with_jobs(self) -> list[tuple[Application, Job]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT applications.*, jobs.id AS job_id_full, jobs.refnr, jobs.titel,
                          jobs.firma, jobs.ort, jobs.url, jobs.beschreibung,
                          jobs.veroeffentlicht_am, jobs.match_score, jobs.status AS job_status,
                          jobs.first_seen
                   FROM applications
                   JOIN jobs ON jobs.id = applications.job_id
                   ORDER BY applications.erstellt_am DESC"""
            ).fetchall()

        result = []
        for row in rows:
            application = Application(
                id=row["id"],
                job_id=row["job_id"],
                anschreiben_text=row["anschreiben_text"],
                pdf_pfad=row["pdf_pfad"],
                kontakt_email=row["kontakt_email"],
                status=row["status"],
                status_quelle=row["status_quelle"],
                erstellt_am=row["erstellt_am"],
                versendet_am=row["versendet_am"],
                message_id=row["message_id"],
            )
            job = Job(
                id=row["job_id_full"],
                refnr=row["refnr"],
                titel=row["titel"],
                firma=row["firma"],
                ort=row["ort"],
                url=row["url"],
                beschreibung=row["beschreibung"],
                veroeffentlicht_am=row["veroeffentlicht_am"],
                match_score=row["match_score"],
                status=row["job_status"],
                first_seen=row["first_seen"],
            )
            result.append((application, job))
        return result

    def find_application_by_message_id(self, message_ids: list[str]) -> Optional[Application]:
        if not message_ids:
            return None
        with self._connect() as conn:
            placeholders = ", ".join("?" for _ in message_ids)
            row = conn.execute(
                f"SELECT * FROM applications WHERE message_id IN ({placeholders})", message_ids
            ).fetchone()
            return Application.from_row(row) if row else None

    def find_applications_by_contact_email(self, email: str) -> list[Application]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM applications WHERE kontakt_email = ? AND status = 'versendet'",
                (email,),
            ).fetchall()
            return [Application.from_row(r) for r in rows]
