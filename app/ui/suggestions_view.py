"""Vorschlagsliste: gefundene Stellen mit Match-Score, Bestaetigen/Ablehnen."""
from __future__ import annotations

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.crypto import Vault
from app.core.database import Database, Job
from app.core.profile import Profile
from app.ui.cover_letter_dialog import CoverLetterDialog
from app.ui.widgets import size_button_to_text


class SuggestionsView(QWidget):
    COLUMNS = ["Titel", "Firma", "Ort", "Score", "Anzeige", "Aktionen"]

    def __init__(self, profile: Profile, vault: Vault, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.db = db

        title = QLabel("Vorschlaege")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        jobs = self.db.list_jobs(status="neu")
        # clearContents() VOR setRowCount(): setCellWidget() ersetzt zwar laut
        # Doku alte Zellen-Widgets automatisch, in der Praxis blieben dabei
        # aber verwaiste Buttons als Geister-Elemente an alten Positionen
        # stehen, sobald refresh() ein zweites Mal lief (z.B. erneuter
        # Tab-Wechsel). clearContents() raeumt zuverlaessig auf.
        self.table.clearContents()
        self.table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            self.table.setItem(row, 0, QTableWidgetItem(job.titel))
            self.table.setItem(row, 1, QTableWidgetItem(job.firma))
            self.table.setItem(row, 2, QTableWidgetItem(job.ort))
            score_item = QTableWidgetItem(f"{job.match_score}%")
            score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, score_item)

            link_btn = QPushButton("Oeffnen")
            link_btn.clicked.connect(lambda _, url=job.url: QDesktopServices.openUrl(QUrl(url)))
            size_button_to_text(link_btn)
            self.table.setCellWidget(row, 4, link_btn)

            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            confirm_btn = QPushButton("Bestaetigen")
            reject_btn = QPushButton("Ablehnen")
            confirm_btn.clicked.connect(lambda _, j=job: self._on_confirm(j))
            reject_btn.clicked.connect(lambda _, j=job: self._on_reject(j))
            size_button_to_text(confirm_btn)
            size_button_to_text(reject_btn)
            actions_layout.addWidget(confirm_btn)
            actions_layout.addWidget(reject_btn)
            self.table.setCellWidget(row, 5, actions)

        self.table.resizeRowsToContents()
        # Jede Nicht-Stretch-Spalte einzeln anpassen (2=Ort, 3=Score,
        # 4=Anzeige, 5=Aktionen) - NICHT resizeColumnsToContents() fuer die
        # ganze Tabelle: das wuerde auch die Stretch-Spalten (0=Titel,
        # 1=Firma) auf ihre aktuelle Inhaltsbreite fixieren und bei langen
        # Firmennamen die sichtbare Fensterbreite sprengen.
        for column in (2, 3, 4, 5):
            self.table.resizeColumnToContents(column)

    def _on_confirm(self, job: Job) -> None:
        self.db.set_job_status(job.id, "bestaetigt")
        application_id = self.db.create_application(job.id)
        dialog = CoverLetterDialog(self.profile, self.vault, self.db, job, application_id, self)
        dialog.exec()
        self.refresh()

    def _on_reject(self, job: Job) -> None:
        self.db.set_job_status(job.id, "abgelehnt")
        self.refresh()
