"""QThread-Wrapper fuer den Claude-API-Call zur Anschreiben-Generierung."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.cover_letter import CoverLetterError, generate_cover_letter
from app.core.profile import Profile


class CoverLetterWorker(QThread):
    finished_ok = Signal(object)  # CoverLetterResult
    failed = Signal(str)

    def __init__(
        self,
        profile: Profile,
        api_key: str,
        job_titel: str,
        arbeitgeber: str,
        ort: str,
        beschreibung: str,
        ansprechpartner: str | None,
        model: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.api_key = api_key
        self.job_titel = job_titel
        self.arbeitgeber = arbeitgeber
        self.ort = ort
        self.beschreibung = beschreibung
        self.ansprechpartner = ansprechpartner
        self.model = model

    def run(self) -> None:
        try:
            result = generate_cover_letter(
                profile=self.profile,
                api_key=self.api_key,
                job_titel=self.job_titel,
                arbeitgeber=self.arbeitgeber,
                ort=self.ort,
                beschreibung=self.beschreibung,
                ansprechpartner=self.ansprechpartner,
                model=self.model,
            )
            self.finished_ok.emit(result)
        except CoverLetterError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # unerwartete API-/Netzwerkfehler abfangen
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
