"""Anschreiben-Vorschau/Bearbeitung, PDF-Erzeugung und Freigabe.

Wird ausschliesslich nach manueller Bestaetigung einer Stelle geoeffnet
(siehe suggestions_view.py) - die Anschreiben-Generierung passiert nie
automatisch im Hintergrund.
"""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from app.config import DEFAULT_CLAUDE_MODEL, cover_letters_dir
from app.core.cover_letter import extract_contact_email
from app.core.crypto import Vault
from app.core.database import Database, Job
from app.core.pdf_generator import generate_cover_letter_pdf
from app.core.profile import Profile
from app.workers.cover_letter_worker import CoverLetterWorker

CLAUDE_MODELS = ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"]


class CoverLetterDialog(QDialog):
    def __init__(
        self,
        profile: Profile,
        vault: Vault,
        db: Database,
        job: Job,
        application_id: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.db = db
        self.job = job
        self.application_id = application_id
        self.pdf_path = cover_letters_dir(profile.slug) / f"{job.refnr}.pdf"
        self.worker: CoverLetterWorker | None = None

        self.setWindowTitle(f"Anschreiben - {job.titel}")
        self.setMinimumSize(700, 650)

        info = QLabel(f"<b>{job.titel}</b> bei {job.firma} ({job.ort}) - Match-Score {job.match_score}%")
        info.setWordWrap(True)

        job_text = QTextBrowser()
        job_text.setPlainText(job.beschreibung)
        job_text.setMaximumHeight(140)

        form = QFormLayout()
        self.ansprechpartner_name_input = QLineEdit()
        self.ansprechpartner_name_input.setPlaceholderText(
            "Optional, z.B. 'Herr Müller' - leer lassen fuer 'Sehr geehrte Damen und Herren,'"
        )
        self.kontakt_email_input = QLineEdit(extract_contact_email(job.beschreibung) or "")
        self.kontakt_email_input.setPlaceholderText("E-Mail-Adresse fuer den Versand")
        self.model_input = QComboBox()
        self.model_input.addItems(CLAUDE_MODELS)
        self.model_input.setCurrentText(self.vault.get("claude_model", DEFAULT_CLAUDE_MODEL))
        form.addRow("Ansprechpartner (Name, fuer Anrede):", self.ansprechpartner_name_input)
        form.addRow("Kontakt-E-Mail (fuer Versand):", self.kontakt_email_input)
        form.addRow("Claude-Modell:", self.model_input)

        self.generate_btn = QPushButton("Anschreiben generieren")
        self.generate_btn.clicked.connect(self._on_generate)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Noch kein Anschreiben generiert. Klicke auf 'Anschreiben generieren'."
        )

        self.status_label = QLabel("")

        pdf_row = QHBoxLayout()
        self.pdf_btn = QPushButton("PDF erzeugen && anzeigen")
        self.pdf_btn.clicked.connect(self._on_generate_pdf)
        self.approve_btn = QPushButton("Freigeben")
        self.approve_btn.clicked.connect(self._on_approve)
        self.approve_btn.setEnabled(False)
        pdf_row.addWidget(self.pdf_btn)
        pdf_row.addWidget(self.approve_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(QLabel("Stellenbeschreibung:"))
        layout.addWidget(job_text)
        layout.addLayout(form)
        layout.addWidget(self.generate_btn)
        layout.addWidget(QLabel("Anschreiben (bearbeitbar):"))
        layout.addWidget(self.text_edit)
        layout.addWidget(self.status_label)
        layout.addLayout(pdf_row)

    def _on_generate(self) -> None:
        api_key = self.vault.get("anthropic_api_key", "")
        if not api_key:
            QMessageBox.warning(
                self,
                "Kein API-Key",
                "Bitte hinterlege zuerst deinen Anthropic-API-Key im Profil-Tab.",
            )
            return

        self.generate_btn.setEnabled(False)
        self.status_label.setText("Anschreiben wird generiert...")

        self.worker = CoverLetterWorker(
            profile=self.profile,
            api_key=api_key,
            job_titel=self.job.titel,
            arbeitgeber=self.job.firma,
            ort=self.job.ort,
            beschreibung=self.job.beschreibung,
            ansprechpartner=self.ansprechpartner_name_input.text().strip() or None,
            model=self.model_input.currentText(),
        )
        self.worker.finished_ok.connect(self._on_generated)
        self.worker.failed.connect(self._on_generate_failed)
        self.worker.start()

    def _on_generated(self, result) -> None:
        self.generate_btn.setEnabled(True)
        self.text_edit.setPlainText(result.text)

        if result.erkannter_ansprechpartner and not self.ansprechpartner_name_input.text().strip():
            self.ansprechpartner_name_input.setText(result.erkannter_ansprechpartner)
            self.status_label.setText(
                f"Anschreiben generiert - Ansprechpartner '{result.erkannter_ansprechpartner}' "
                "automatisch aus der Anzeige erkannt und eingetragen. Bitte pruefen."
            )
        else:
            self.status_label.setText(
                "Anschreiben generiert - kein Ansprechpartner erkannt, Standardanrede "
                "verwendet. Bitte pruefen und bei Bedarf anpassen."
            )

    def _on_generate_failed(self, message: str) -> None:
        self.generate_btn.setEnabled(True)
        self.status_label.setText("")
        QMessageBox.critical(self, "Fehler", message)

    def _on_generate_pdf(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Kein Text", "Es liegt noch kein Anschreiben-Text vor.")
            return
        generate_cover_letter_pdf(
            output_path=self.pdf_path,
            profile=self.profile,
            empfaenger_firma=self.job.firma,
            empfaenger_ort=self.job.ort,
            betreff=f"Bewerbung als {self.job.titel}",
            brieftext=text,
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.pdf_path)))
        self.approve_btn.setEnabled(True)
        self.status_label.setText("PDF erzeugt. Bitte im geoeffneten Viewer pruefen.")

    def _on_approve(self) -> None:
        if not self.pdf_path.exists():
            QMessageBox.warning(self, "Kein PDF", "Bitte zuerst das PDF erzeugen und pruefen.")
            return
        kontakt_email = self.kontakt_email_input.text().strip()
        if not kontakt_email:
            QMessageBox.warning(
                self,
                "Keine Kontakt-E-Mail",
                "Bitte eine Kontakt-E-Mail-Adresse eintragen - ohne sie kann die Bewerbung "
                "spaeter nicht versendet werden.",
            )
            return
        self.db.update_application(
            self.application_id,
            anschreiben_text=self.text_edit.toPlainText(),
            pdf_pfad=str(self.pdf_path),
            kontakt_email=kontakt_email,
            status="freigegeben",
        )
        QMessageBox.information(
            self,
            "Freigegeben",
            "Das Anschreiben wurde freigegeben und lokal gespeichert.\n"
            "Im Tab 'Bewerbungen' kannst du es jetzt per E-Mail versenden - sofern du den "
            "automatischen Versand in den Einstellungen aktiviert hast (Vorschau-Modus ist "
            "standardmaessig aktiv).",
        )
        self.accept()
