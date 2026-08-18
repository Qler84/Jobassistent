"""Einstellungen: Match-Schwelle, Vorschau-Modus, Standard-Modell, IMAP-Auto-Check."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from app.config import DEFAULT_CLAUDE_MODEL
from app.core.crypto import Vault
from app.core.profile import Profile, ProfileManager

CLAUDE_MODELS = ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"]


class SettingsView(QWidget):
    settings_saved = Signal()

    def __init__(self, profile: Profile, vault: Vault, manager: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.manager = manager

        title = QLabel("Einstellungen")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        self.threshold_label = QLabel()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(profile.match_threshold)
        self.threshold_slider.valueChanged.connect(self._update_threshold_label)
        self._update_threshold_label(profile.match_threshold)

        threshold_info = QLabel(
            "Stellen unterhalb dieser Match-Schwelle werden bei der Suche gar nicht erst "
            "gespeichert oder vorgeschlagen (Qualitaet vor Quantitaet)."
        )
        threshold_info.setWordWrap(True)

        self.model_input = QComboBox()
        self.model_input.addItems(CLAUDE_MODELS)
        self.model_input.setCurrentText(vault.get("claude_model", DEFAULT_CLAUDE_MODEL))

        self.auto_send_checkbox = QCheckBox("Automatischen E-Mail-Versand aktivieren")
        self.auto_send_checkbox.setChecked(profile.auto_send_enabled)

        vorschau_info = QLabel(
            "Standardmaessig laeuft die App im Vorschau-Modus: Anschreiben werden erzeugt und "
            "lokal gespeichert, aber NICHT automatisch versendet. Erst wenn du hier den "
            "automatischen Versand aktivierst, kannst du im Tab 'Bewerbungen' freigegebene "
            "Anschreiben per Klick tatsaechlich versenden - jeder Versand erfordert weiterhin "
            "eine explizite Bestaetigung, es wird nie im Hintergrund automatisch versendet."
        )
        vorschau_info.setWordWrap(True)
        vorschau_info.setStyleSheet("color: #e0a030;")

        self.imap_auto_checkbox = QCheckBox("Postfach automatisch im Hintergrund pruefen")
        self.imap_auto_checkbox.setChecked(bool(vault.get("imap_auto_check_enabled", False)))
        self.imap_interval_input = QSpinBox()
        self.imap_interval_input.setRange(5, 240)
        self.imap_interval_input.setSuffix(" Minuten")
        self.imap_interval_input.setValue(int(vault.get("imap_auto_check_minutes", 30)))

        imap_info = QLabel(
            "Bei aktivierter Option prueft die App in diesem Intervall automatisch per IMAP auf "
            "Antworten und ordnet sie bekannten Bewerbungen zu (manuelle Pruefung ist im Tab "
            "'Bewerbungen' jederzeit zusaetzlich moeglich)."
        )
        imap_info.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Match-Schwelle:", self.threshold_label)
        form.addRow(self.threshold_slider)
        form.addRow(threshold_info)
        form.addRow("Standard-Modell fuer Anschreiben:", self.model_input)
        form.addRow(self.auto_send_checkbox)
        form.addRow(vorschau_info)
        form.addRow(self.imap_auto_checkbox)
        form.addRow("Pruefintervall:", self.imap_interval_input)
        form.addRow(imap_info)

        save_btn = QPushButton("Einstellungen speichern")
        save_btn.clicked.connect(self._on_save)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(save_btn)
        layout.addStretch()

    def _update_threshold_label(self, value: int) -> None:
        self.threshold_label.setText(f"{value}%")

    def _on_save(self) -> None:
        self.profile.match_threshold = self.threshold_slider.value()
        self.profile.auto_send_enabled = self.auto_send_checkbox.isChecked()
        self.manager.save_profile(self.profile)

        self.vault.set("claude_model", self.model_input.currentText())
        self.vault.set("imap_auto_check_enabled", self.imap_auto_checkbox.isChecked())
        self.vault.set("imap_auto_check_minutes", self.imap_interval_input.value())
        self.vault.save()

        QMessageBox.information(self, "Gespeichert", "Einstellungen wurden gespeichert.")
        self.settings_saved.emit()
