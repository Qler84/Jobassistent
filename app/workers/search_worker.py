"""QThread-Wrapper fuer die BA-Jobsuche, damit die UI waehrend Netzwerk-Calls
nicht blockiert."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core import ba_jobsuche, matching
from app.core.database import Database
from app.core.profile import Profile


class SearchWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(int, int, list)  # (neue_treffer, geprueft_gesamt, fehler_je_suchbegriff)
    failed = Signal(str)

    def __init__(
        self,
        profile: Profile,
        db: Database,
        was_liste: list[str],
        wo: str,
        umkreis: int,
        veroeffentlicht_seit: int | None,
        arbeitszeit: str | None,
        size: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.db = db
        self.was_liste = was_liste
        self.wo = wo
        self.umkreis = umkreis
        self.veroeffentlicht_seit = veroeffentlicht_seit
        self.arbeitszeit = arbeitszeit
        self.size = size

    def run(self) -> None:
        # Mehrere Wunschjobtitel = mehrere API-Aufrufe (die BA-API kennt pro
        # Suche nur einen Begriff) - Treffer werden ueber alle Begriffe hinweg
        # per refnr dedupliziert, bevor sie einzeln geprueft werden.
        alle_treffer: dict[str, ba_jobsuche.JobSearchResult] = {}
        fehler: list[str] = []
        for i, was in enumerate(self.was_liste, start=1):
            self.progress.emit(f"Suche '{was}' ({i}/{len(self.was_liste)})...")
            try:
                treffer = ba_jobsuche.search_jobs(
                    was=was,
                    wo=self.wo,
                    umkreis=self.umkreis,
                    veroeffentlicht_seit=self.veroeffentlicht_seit,
                    arbeitszeit=self.arbeitszeit,
                    size=self.size,
                )
            except ba_jobsuche.BAApiError as exc:
                fehler.append(f"'{was}': {exc}")
                continue
            for eintrag in treffer:
                alle_treffer.setdefault(eintrag.refnr, eintrag)

        if not alle_treffer and fehler:
            self.failed.emit("; ".join(fehler))
            return

        treffer_liste = list(alle_treffer.values())
        neue = 0
        geprueft = 0
        for eintrag in treffer_liste:
            if self.db.job_exists(eintrag.refnr):
                continue
            geprueft += 1
            self.progress.emit(f"Pruefe {geprueft}/{len(treffer_liste)}: {eintrag.titel[:60]}")
            try:
                details = ba_jobsuche.get_job_details(eintrag.refnr)
            except ba_jobsuche.BAApiError:
                continue

            score = matching.score_job(self.profile, eintrag.titel, details.beschreibung)
            if score < self.profile.match_threshold:
                continue

            self.db.insert_job(
                refnr=eintrag.refnr,
                titel=eintrag.titel,
                firma=eintrag.arbeitgeber or details.arbeitgeber,
                ort=eintrag.ort or details.ort,
                url=eintrag.url,
                beschreibung=details.beschreibung,
                veroeffentlicht_am=eintrag.veroeffentlicht_am,
                match_score=score,
            )
            neue += 1

        self.finished_ok.emit(neue, len(treffer_liste), fehler)
