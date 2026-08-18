"""QThread-Wrapper fuer den SMTP-Verbindungstest (Profil-Tab)."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.email_smtp import SmtpConfig, SmtpError, test_connection


class SmtpTestWorker(QThread):
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, config: SmtpConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config

    def run(self) -> None:
        try:
            test_connection(self.config)
            self.finished_ok.emit()
        except SmtpError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unerwartete Fehler abfangen, UI nicht crashen lassen
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
