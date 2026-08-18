"""Kennzahlenleiste oberhalb des Inhaltsbereichs (Layout-Option B).

Zeigt drei Kacheln (Neue Treffer, Versendet, Einladungen) auf Basis der
lokalen Datenbank - keine zusaetzlichen API-Aufrufe. Wird bei Navigation und
nach relevanten Aktionen ueber `refresh()` aktualisiert.
"""
from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.core.database import Database


class _MetricTile(QWidget):
    def __init__(self, titel: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("metricTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 500;")
        title_label = QLabel(titel)
        title_label.setStyleSheet("font-size: 12px; color: palette(mid);")

        layout.addWidget(self.value_label)
        layout.addWidget(title_label)

    def set_value(self, value: int) -> None:
        self.value_label.setText(str(value))


class DashboardBar(QWidget):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setObjectName("dashboardBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.tile_neu = _MetricTile("Neue Treffer")
        self.tile_versendet = _MetricTile("Versendet")
        self.tile_einladung = _MetricTile("Einladungen")

        for tile in (self.tile_neu, self.tile_versendet, self.tile_einladung):
            layout.addWidget(tile)
        layout.addStretch()

        self.refresh()

    def refresh(self) -> None:
        self.tile_neu.set_value(len(self.db.list_jobs(status="neu")))
        self.tile_versendet.set_value(len(self.db.list_applications(status="versendet")))
        self.tile_einladung.set_value(len(self.db.list_applications(status="einladung")))
