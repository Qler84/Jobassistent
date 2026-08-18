"""QThread-Wrapper fuer die IMAP-Postfachpruefung (manuell oder periodisch)."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.database import Database
from app.core.email_imap import ImapConfig, ImapError
from app.core.status_tracking import run_imap_check


class ImapCheckWorker(QThread):
    finished_ok = Signal(object)  # list[StatusUpdate]
    failed = Signal(str)

    def __init__(self, config: ImapConfig, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.db = db

    def run(self) -> None:
        try:
            updates = run_imap_check(self.config, self.db)
            self.finished_ok.emit(updates)
        except ImapError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unerwartete Fehler abfangen, UI nicht crashen lassen
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
