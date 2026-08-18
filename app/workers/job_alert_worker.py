"""QThread-Wrapper fuer den Job-Alert-E-Mail-Import (IMAP + Claude)."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.database import Database
from app.core.email_imap import ImapConfig, ImapError
from app.core.job_alert_import import run_job_alert_import
from app.core.profile import Profile


class JobAlertWorker(QThread):
    finished_ok = Signal(object)  # JobAlertResult
    failed = Signal(str)

    def __init__(
        self,
        imap_config: ImapConfig,
        profile: Profile,
        db: Database,
        api_key: str,
        model: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.imap_config = imap_config
        self.profile = profile
        self.db = db
        self.api_key = api_key
        self.model = model

    def run(self) -> None:
        try:
            result = run_job_alert_import(
                imap_config=self.imap_config,
                profile=self.profile,
                db=self.db,
                api_key=self.api_key,
                model=self.model,
            )
            self.finished_ok.emit(result)
        except ImapError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unerwartete Fehler abfangen, UI nicht crashen lassen
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
