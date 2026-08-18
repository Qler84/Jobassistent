"""QThread-Wrapper fuer den Profil-Import aus Lebenslauf/Zeugnis-PDFs via Claude."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.profile_import import ProfileImportError, extract_profile_from_documents


class ProfileImportWorker(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, api_key: str, pdf_paths: list[Path], model: str, parent=None) -> None:
        super().__init__(parent)
        self.api_key = api_key
        self.pdf_paths = pdf_paths
        self.model = model

    def run(self) -> None:
        try:
            data = extract_profile_from_documents(self.api_key, self.pdf_paths, self.model)
            self.finished_ok.emit(data)
        except ProfileImportError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unerwartete Fehler abfangen, UI nicht crashen lassen
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
