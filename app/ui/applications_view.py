"""Bewerbungen-Tab: Status-Uebersicht, manueller Versand, IMAP-Status-Check.

Versand ist nur moeglich, wenn eine Bewerbung bereits ueber den
Anschreiben-Dialog freigegeben wurde UND der Nutzer den Auto-Versand in den
Einstellungen aktiviert hat (Vorschau-Modus ist Standard - siehe
settings_view.py). Es wird nie im Hintergrund automatisch versendet; jeder
Versand erfordert einen expliziten Klick plus Bestaetigung.

Das Anschreiben wird als E-Mail-Text versendet (nicht als PDF-Anhang) - das
generierte PDF dient nur der lokalen Vorschau/Kontrolle vor der Freigabe.
Angehaengt werden ausschliesslich die im Profil hinterlegten Anlagen (siehe
profile_editor.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import anlagen_dir
from app.core.crypto import Vault
from app.core.database import Application, Database, Job
from app.core.email_imap import ImapConfig
from app.core.email_smtp import SmtpConfig
from app.core.profile import Profile
from app.ui.widgets import size_button_to_text
from app.workers.imap_check_worker import ImapCheckWorker
from app.workers.send_worker import SmtpSendWorker

STATUS_LABELS = {
    "entwurf": "Entwurf",
    "freigegeben": "Freigegeben",
    "versendet": "Versendet",
    "antwort_erhalten": "Antwort erhalten",
    "einladung": "Einladung zum Gespraech",
    "absage": "Absage",
    "keine_rueckmeldung": "Keine Rueckmeldung",
}
STATUS_ORDER = list(STATUS_LABELS.keys())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _SendPreviewDialog(QDialog):
    """Zeigt die tatsaechlich zu versendende E-Mail (Empfaenger, Betreff,
    voller Text, Anhaenge) vor der letzten Bestaetigung an."""

    def __init__(
        self, empfaenger: str, betreff: str, text: str, anhaenge: list[Path], parent=None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vorschau: Bewerbung versenden")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.addRow("An:", QLabel(empfaenger))
        form.addRow("Betreff:", QLabel(betreff))
        anhang_text = ", ".join(p.name for p in anhaenge) if anhaenge else "(keine)"
        anhang_label = QLabel(anhang_text)
        anhang_label.setWordWrap(True)
        form.addRow("Anhaenge:", anhang_label)
        layout.addLayout(form)

        layout.addWidget(QLabel("Nachricht:"))
        body = QTextEdit()
        body.setPlainText(text)
        body.setReadOnly(True)
        layout.addWidget(body)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Jetzt senden")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class ApplicationsView(QWidget):
    COLUMNS = ["Titel", "Firma", "Status", "Quelle", "Versendet am", "Aktionen"]

    def __init__(self, profile: Profile, vault: Vault, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.db = db
        self.send_worker: SmtpSendWorker | None = None
        self.imap_worker: ImapCheckWorker | None = None

        title = QLabel("Bewerbungen")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        top_row = QHBoxLayout()
        self.check_inbox_btn = QPushButton("Postfach jetzt pruefen")
        self.check_inbox_btn.clicked.connect(self.check_inbox)
        top_row.addWidget(self.check_inbox_btn)
        top_row.addStretch()

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(top_row)
        layout.addWidget(self.table)
        layout.addWidget(self.status_label)

        self.refresh()

    # --- Aufbau -------------------------------------------------------

    def refresh(self) -> None:
        rows = self.db.list_applications_with_jobs()
        # clearContents() VOR setRowCount(): siehe Kommentar in
        # suggestions_view.py.refresh() - ohne das blieben bei wiederholtem
        # Aufruf (z.B. erneuter Tab-Wechsel) alte Combobox-/Button-Widgets
        # als Geister-Elemente an alten Positionen sichtbar.
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        for row, (application, job) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(job.titel))
            self.table.setItem(row, 1, QTableWidgetItem(job.firma))

            status_combo = QComboBox()
            for value in STATUS_ORDER:
                status_combo.addItem(STATUS_LABELS[value], value)
            status_combo.setCurrentIndex(STATUS_ORDER.index(application.status))
            status_combo.currentIndexChanged.connect(
                lambda _, a=application, c=status_combo: self._on_status_changed(a, c)
            )
            self.table.setCellWidget(row, 2, status_combo)

            quelle_item = QTableWidgetItem(
                "Automatisch" if application.status_quelle == "auto" else "Manuell"
            )
            quelle_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, quelle_item)

            versendet_text = ""
            if application.versendet_am:
                versendet_text = application.versendet_am.split("T")[0]
            self.table.setItem(row, 4, QTableWidgetItem(versendet_text))

            self.table.setCellWidget(row, 5, self._build_actions(application, job))

        self.table.resizeRowsToContents()
        # Jede Nicht-Stretch-Spalte einzeln anpassen (2=Status, 3=Quelle,
        # 4=Versendet am, 5=Aktionen) - NICHT resizeColumnsToContents() fuer
        # die ganze Tabelle, das wuerde auch die Stretch-Spalten (0=Titel,
        # 1=Firma) auf ihre aktuelle Inhaltsbreite fixieren und bei langen
        # Firmennamen die sichtbare Fensterbreite sprengen.
        for column in (2, 3, 4, 5):
            self.table.resizeColumnToContents(column)

    def _build_actions(self, application: Application, job: Job) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        send_btn = QPushButton("Jetzt senden")
        enabled, reason = self._can_send(application)
        send_btn.setEnabled(application.status == "freigegeben" and enabled)
        if application.status != "freigegeben":
            send_btn.setToolTip("Nur freigegebene Bewerbungen (aus dem Anschreiben-Dialog) koennen versendet werden.")
        elif not enabled:
            send_btn.setToolTip(reason)
        send_btn.clicked.connect(lambda _, a=application, j=job: self._on_send(a, j))
        size_button_to_text(send_btn)
        layout.addWidget(send_btn)
        return widget

    # --- Status manuell korrigieren -------------------------------------

    def _on_status_changed(self, application: Application, combo: QComboBox) -> None:
        new_status = combo.currentData()
        if new_status == application.status:
            return
        self.db.update_application(application.id, status=new_status, status_quelle="manuell")
        self.refresh()

    # --- Versand ---------------------------------------------------------

    def _can_send(self, application: Application) -> tuple[bool, str]:
        if not self.profile.auto_send_enabled:
            return False, "Vorschau-Modus aktiv - aktiviere den Versand in den Einstellungen."
        if not self.vault.get("smtp_host") or not self.vault.get("smtp_user") or not self.vault.get(
            "smtp_password"
        ):
            return False, "Keine vollstaendigen SMTP-Zugangsdaten im Profil hinterlegt."
        if not application.kontakt_email:
            return False, "Keine Kontakt-E-Mail-Adresse fuer diese Bewerbung hinterlegt."
        if not application.pdf_pfad or not Path(application.pdf_pfad).exists():
            return False, "Anschreiben wurde noch nicht zur Kontrolle als PDF erzeugt."
        return True, ""

    def _on_send(self, application: Application, job: Job) -> None:
        enabled, reason = self._can_send(application)
        if not enabled:
            QMessageBox.warning(self, "Versand nicht moeglich", reason)
            return

        betreff = f"Bewerbung als {job.titel}"
        text = application.anschreiben_text or ""
        anlagen_ordner = anlagen_dir(self.profile.slug)
        anhaenge = [anlagen_ordner / name for name in self.profile.anlagen]

        preview = _SendPreviewDialog(application.kontakt_email, betreff, text, anhaenge, self)
        if preview.exec() != QDialog.Accepted:
            return

        smtp_port = int(self.vault.get("smtp_port", 465))
        config = SmtpConfig(
            host=self.vault.get("smtp_host"),
            port=smtp_port,
            user=self.vault.get("smtp_user"),
            password=self.vault.get("smtp_password"),
            # Port 465 = implizites SSL; alle anderen Ports (z.B. 587) = STARTTLS.
            use_ssl=(smtp_port == 465),
        )

        self.send_worker = SmtpSendWorker(
            config=config,
            empfaenger=application.kontakt_email,
            betreff=betreff,
            text=text,
            anhaenge=anhaenge,
            absender_name=self.profile.name,
        )
        self.send_worker.finished_ok.connect(
            lambda message_id, a=application: self._on_send_done(a, message_id)
        )
        self.send_worker.failed.connect(self._on_send_failed)
        self.status_label.setText("Versand laeuft...")
        self.send_worker.start()

    def _on_send_done(self, application: Application, message_id: str) -> None:
        self.db.update_application(
            application.id, status="versendet", versendet_am=_now_iso(), message_id=message_id
        )
        self.status_label.setText("Bewerbung wurde versendet.")
        self.refresh()

    def _on_send_failed(self, message: str) -> None:
        self.status_label.setText("")
        QMessageBox.critical(self, "Versand fehlgeschlagen", message)

    # --- IMAP-Check --------------------------------------------------------

    def check_inbox(self) -> None:
        """Startet eine IMAP-Pruefung. Oeffentlich, damit sie sowohl vom Button
        als auch vom periodischen Timer in main_window.py ausgeloest werden kann."""
        if self.imap_worker is not None and self.imap_worker.isRunning():
            return
        if not self.vault.get("imap_host") or not self.vault.get("smtp_user") or not self.vault.get(
            "smtp_password"
        ):
            QMessageBox.warning(
                self,
                "IMAP nicht konfiguriert",
                "Bitte hinterlege im Profil-Tab mindestens den IMAP-Server sowie E-Mail-Adresse "
                "und Passwort (werden fuer SMTP und IMAP gemeinsam genutzt).",
            )
            return

        config = ImapConfig(
            host=self.vault.get("imap_host"),
            port=int(self.vault.get("imap_port", 993)),
            user=self.vault.get("smtp_user"),
            password=self.vault.get("smtp_password"),
        )
        self.check_inbox_btn.setEnabled(False)
        self.status_label.setText("Postfach wird geprueft...")

        self.imap_worker = ImapCheckWorker(config=config, db=self.db)
        self.imap_worker.finished_ok.connect(self._on_check_done)
        self.imap_worker.failed.connect(self._on_check_failed)
        self.imap_worker.start()

    def _on_check_done(self, updates: list) -> None:
        self.check_inbox_btn.setEnabled(True)
        if not updates:
            self.status_label.setText("Postfach geprueft: keine neuen zuordenbaren Antworten gefunden.")
        else:
            zusammenfassung = ", ".join(
                f"#{u.application_id} -> {STATUS_LABELS.get(u.neuer_status, u.neuer_status)}"
                for u in updates
            )
            self.status_label.setText(f"{len(updates)} Antwort(en) zugeordnet: {zusammenfassung}")
        self.refresh()

    def _on_check_failed(self, message: str) -> None:
        self.check_inbox_btn.setEnabled(True)
        self.status_label.setText("")
        QMessageBox.critical(self, "Fehler bei der Postfachpruefung", message)
