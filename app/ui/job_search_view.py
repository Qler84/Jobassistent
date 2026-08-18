"""Sucheingaben und Start der Jobsuche gegen die BA-API sowie Import aus
Job-Alert-E-Mails (LinkedIn/Xing/StepStone/Indeed)."""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_CLAUDE_MODEL
from app.core.ba_jobsuche import ARBEITSZEIT_CODES
from app.core.crypto import Vault
from app.core.database import Database
from app.core.email_imap import ImapConfig
from app.core.profile import Profile
from app.workers.job_alert_worker import JobAlertWorker
from app.workers.search_worker import SearchWorker


class JobSearchView(QWidget):
    def __init__(
        self,
        profile: Profile,
        vault: Vault,
        db: Database,
        on_search_done: Callable[[], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.db = db
        self.on_search_done = on_search_done
        self.worker: SearchWorker | None = None
        self.job_alert_worker: JobAlertWorker | None = None

        title = QLabel("Jobsuche (Bundesagentur fuer Arbeit)")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.was_input = QLineEdit()
        self.was_input.setPlaceholderText(
            "Optional zusaetzlich - alle Wunschjobtitel aus dem Profil werden automatisch durchsucht"
        )
        self.wo_input = QLineEdit(profile.wunschort)
        self.umkreis_input = QSpinBox()
        self.umkreis_input.setRange(0, 200)
        self.umkreis_input.setSuffix(" km")
        self.umkreis_input.setValue(profile.umkreis_km)

        self.tage_input = QSpinBox()
        self.tage_input.setRange(0, 100)
        self.tage_input.setValue(14)
        self.tage_input.setSuffix(" Tage")

        self.arbeitszeit_input = QComboBox()
        self.arbeitszeit_input.addItem("Alle", "")
        for label, code in ARBEITSZEIT_CODES.items():
            self.arbeitszeit_input.addItem(label, code)

        self.size_input = QSpinBox()
        self.size_input.setRange(5, 100)
        self.size_input.setValue(25)

        form = QFormLayout()
        form.addRow("Zusaetzlicher Suchbegriff (optional):", self.was_input)
        form.addRow("Ort (wo):", self.wo_input)
        form.addRow("Umkreis:", self.umkreis_input)
        form.addRow("Veroeffentlicht seit:", self.tage_input)
        form.addRow("Arbeitszeit:", self.arbeitszeit_input)
        form.addRow("Max. Treffer pro Suchbegriff:", self.size_input)

        self.start_btn = QPushButton("Suche starten")
        self.start_btn.clicked.connect(self._on_start)

        wunschjobtitel_info = (
            ", ".join(profile.wunschjobtitel)
            if profile.wunschjobtitel
            else "(keine im Profil hinterlegt)"
        )
        self.status_label = QLabel(
            f"Match-Schwelle: {profile.match_threshold}% (nur Treffer darueber werden vorgeschlagen). "
            f"Durchsuchte Wunschjobtitel: {wunschjobtitel_info}"
        )
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.status_label)

        trenner = QFrame()
        trenner.setFrameShape(QFrame.HLine)
        layout.addWidget(trenner)

        layout.addWidget(self._build_job_alert_group())
        layout.addStretch()

    def _build_job_alert_group(self) -> QGroupBox:
        box = QGroupBox("Job-Alert-E-Mails importieren (LinkedIn, Xing, StepStone, Indeed)")
        inner = QVBoxLayout(box)
        info = QLabel(
            "Kein Scraping: es werden nur E-Mails ausgewertet, die diese Portale dir bereits "
            "regulaer schicken, wenn du dort eine gespeicherte Suche/einen Job-Alert "
            "einrichtest. Die App liest dein Postfach per IMAP (dieselben Zugangsdaten wie "
            "beim Status-Tracking im Bewerbungen-Tab) und laesst Claude die enthaltenen "
            "Stellenangebote extrahieren - Matching und Speicherung laufen genauso wie bei "
            "der BA-Suche."
        )
        info.setWordWrap(True)
        inner.addWidget(info)

        self.job_alert_btn = QPushButton("Job-Alert-E-Mails jetzt pruefen")
        self.job_alert_btn.clicked.connect(self._on_check_job_alerts)
        inner.addWidget(self.job_alert_btn)

        self.job_alert_status_label = QLabel("")
        self.job_alert_status_label.setWordWrap(True)
        inner.addWidget(self.job_alert_status_label)

        return box

    def _on_start(self) -> None:
        begriffe = list(self.profile.wunschjobtitel)
        zusatz = self.was_input.text().strip()
        if zusatz and zusatz.lower() not in (b.lower() for b in begriffe):
            begriffe.append(zusatz)
        if not begriffe:
            QMessageBox.warning(
                self,
                "Fehlt",
                "Bitte mindestens einen Wunschjobtitel im Profil hinterlegen oder hier einen "
                "Suchbegriff eingeben.",
            )
            return

        self.start_btn.setEnabled(False)
        self.status_label.setText("Suche laeuft...")

        self.worker = SearchWorker(
            profile=self.profile,
            db=self.db,
            was_liste=begriffe,
            wo=self.wo_input.text().strip(),
            umkreis=self.umkreis_input.value(),
            veroeffentlicht_seit=self.tage_input.value(),
            arbeitszeit=self.arbeitszeit_input.currentData() or None,
            size=self.size_input.value(),
        )
        self.worker.progress.connect(self.status_label.setText)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_finished(self, neue: int, geprueft: int, fehler: list[str]) -> None:
        self.start_btn.setEnabled(True)
        text = (
            f"Fertig: {neue} neue Treffer oberhalb der Match-Schwelle gespeichert "
            f"({geprueft} neue Anzeigen geprueft)."
        )
        if fehler:
            text += f" {len(fehler)} Suchbegriff(e) fehlgeschlagen: " + "; ".join(fehler)
        self.status_label.setText(text)
        self.on_search_done()

    def _on_failed(self, message: str) -> None:
        self.start_btn.setEnabled(True)
        self.status_label.setText("Fehler bei der Suche.")
        QMessageBox.critical(self, "Fehler", message)

    # --- Job-Alert-E-Mail-Import ------------------------------------------

    def _on_check_job_alerts(self) -> None:
        api_key = self.vault.get("anthropic_api_key", "")
        if not api_key:
            QMessageBox.warning(
                self,
                "Kein API-Key",
                "Bitte hinterlege zuerst deinen Anthropic-API-Key im Profil-Tab.",
            )
            return
        if not self.vault.get("imap_host") or not self.vault.get("smtp_user") or not self.vault.get(
            "smtp_password"
        ):
            QMessageBox.warning(
                self,
                "IMAP nicht konfiguriert",
                "Bitte hinterlege im Profil-Tab mindestens den IMAP-Server sowie E-Mail-Adresse "
                "und Passwort.",
            )
            return

        imap_config = ImapConfig(
            host=self.vault.get("imap_host"),
            port=int(self.vault.get("imap_port", 993)),
            user=self.vault.get("smtp_user"),
            password=self.vault.get("smtp_password"),
        )
        model = self.vault.get("claude_model", DEFAULT_CLAUDE_MODEL)

        self.job_alert_btn.setEnabled(False)
        self.job_alert_status_label.setText("Postfach wird nach Job-Alert-Mails durchsucht...")

        self.job_alert_worker = JobAlertWorker(
            imap_config=imap_config,
            profile=self.profile,
            db=self.db,
            api_key=api_key,
            model=model,
        )
        self.job_alert_worker.finished_ok.connect(self._on_job_alerts_done)
        self.job_alert_worker.failed.connect(self._on_job_alerts_failed)
        self.job_alert_worker.start()

    def _on_job_alerts_done(self, result) -> None:
        self.job_alert_btn.setEnabled(True)
        text = (
            f"{result.emails_gefunden} Job-Alert-Mail(s) gefunden, "
            f"{result.emails_verarbeitet} verarbeitet, {result.jobs_neu} neue Treffer "
            f"oberhalb der Match-Schwelle gespeichert."
        )
        if result.fehler:
            text += f" {len(result.fehler)} Mail(s) konnten nicht ausgewertet werden."
        if result.emails_gefunden == 0:
            if result.ungelesene_absender:
                text += " Ungelesene Mail(s) im Postfach von: " + ", ".join(
                    result.ungelesene_absender
                )
            else:
                text += " Keine ungelesenen Mails im Postfach gefunden."
        self.job_alert_status_label.setText(text)
        if result.jobs_neu:
            self.on_search_done()

    def _on_job_alerts_failed(self, message: str) -> None:
        self.job_alert_btn.setEnabled(True)
        self.job_alert_status_label.setText("")
        QMessageBox.critical(self, "Fehler", message)
