"""QThread-Wrapper fuer den SMTP-Versand einer einzelnen Bewerbung."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.email_smtp import SmtpConfig, SmtpError, send_application_email


class SmtpSendWorker(QThread):
    finished_ok = Signal(str)  # Message-ID der versendeten Mail
    failed = Signal(str)

    def __init__(
        self,
        config: SmtpConfig,
        empfaenger: str,
        betreff: str,
        text: str,
        anhaenge: list[Path],
        absender_name: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.empfaenger = empfaenger
        self.betreff = betreff
        self.text = text
        self.anhaenge = anhaenge
        self.absender_name = absender_name

    def run(self) -> None:
        try:
            message_id = send_application_email(
                config=self.config,
                empfaenger=self.empfaenger,
                betreff=self.betreff,
                text=self.text,
                anhaenge=self.anhaenge,
                absender_name=self.absender_name,
            )
            self.finished_ok.emit(message_id)
        except SmtpError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unerwartete Fehler abfangen, UI nicht crashen lassen
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
