"""Profil-Auswahl und Anmeldung mit Master-Passwort."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import ICON_PATH
from app.core.crypto import WrongPasswordError
from app.core.profile import Profile, ProfileManager
from app.core.crypto import Vault


class NewProfileDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neues Profil anlegen")
        self.setMinimumWidth(360)

        self.name_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_confirm_input = QLineEdit()
        self.password_confirm_input.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Anzeigename:", self.name_input)
        form.addRow("Master-Passwort:", self.password_input)
        form.addRow("Passwort wiederholen:", self.password_confirm_input)

        hinweis = QLabel(
            "Das Master-Passwort schuetzt deine hinterlegten Zugangsdaten (E-Mail, API-Keys).\n"
            "Es wird nirgendwo gespeichert - bei Verlust koennen die Zugangsdaten nicht\n"
            "wiederhergestellt werden."
        )
        hinweis.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hinweis)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Fehlt", "Bitte einen Anzeigenamen eingeben.")
            return
        if len(self.password_input.text()) < 8:
            QMessageBox.warning(self, "Zu kurz", "Das Master-Passwort sollte mindestens 8 Zeichen haben.")
            return
        if self.password_input.text() != self.password_confirm_input.text():
            QMessageBox.warning(self, "Stimmt nicht ueberein", "Die Passwoerter stimmen nicht ueberein.")
            return
        self.accept()


class LoginWindow(QWidget):
    login_successful = Signal(object, object)  # (Profile, Vault)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Job-Assistent - Anmeldung")
        self.setMinimumSize(420, 420)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.manager = ProfileManager()

        title = QLabel("Job-Assistent")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel("Profil auswaehlen und mit Master-Passwort anmelden")
        subtitle.setStyleSheet("color: #888;")

        self.profile_list = QListWidget()
        self.profile_list.itemSelectionChanged.connect(self._on_selection_changed)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Master-Passwort")
        self.password_input.returnPressed.connect(self._on_login)

        self.login_btn = QPushButton("Anmelden")
        self.login_btn.clicked.connect(self._on_login)
        self.new_profile_btn = QPushButton("Neues Profil anlegen")
        self.new_profile_btn.clicked.connect(self._on_new_profile)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.new_profile_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.login_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(QLabel("Profile:"))
        layout.addWidget(self.profile_list)
        layout.addWidget(self.password_input)
        layout.addLayout(btn_row)

        self._refresh_profiles()

    def _refresh_profiles(self) -> None:
        self.profile_list.clear()
        for entry in self.manager.list_profiles():
            item = QListWidgetItem(entry.display_name)
            item.setData(1, entry.slug)
            self.profile_list.addItem(item)
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        has_selection = self.profile_list.currentItem() is not None
        self.login_btn.setEnabled(has_selection)

    def _on_login(self) -> None:
        item = self.profile_list.currentItem()
        if item is None:
            return
        slug = item.data(1)
        password = self.password_input.text()
        try:
            profile, vault = self.manager.login(slug, password)
        except WrongPasswordError:
            QMessageBox.critical(self, "Falsches Passwort", "Das Master-Passwort ist falsch.")
            self.password_input.clear()
            return
        except FileNotFoundError:
            QMessageBox.critical(self, "Fehler", "Profildaten konnten nicht gefunden werden.")
            return

        self.login_successful.emit(profile, vault)

    def _on_new_profile(self) -> None:
        dialog = NewProfileDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name = dialog.name_input.text().strip()
        password = dialog.password_input.text()
        profile, vault = self.manager.create_profile(name, password)
        self._refresh_profiles()
        QMessageBox.information(
            self, "Profil angelegt", f"Profil '{name}' wurde angelegt. Du bist jetzt angemeldet."
        )
        self.login_successful.emit(profile, vault)
