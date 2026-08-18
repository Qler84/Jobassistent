"""Einstiegspunkt: python -m app.main"""
from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.config import ICON_PATH
from app.core.crypto import Vault
from app.core.profile import Profile
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


class AppController:
    """Haelt Referenzen auf Login- und Hauptfenster, damit sie nicht vom
    Garbage Collector eingesammelt werden, und wechselt zwischen beiden."""

    def __init__(self) -> None:
        self.login_window: LoginWindow | None = LoginWindow()
        self.main_window: MainWindow | None = None
        self.login_window.login_successful.connect(self._on_login_successful)
        self.login_window.show()

    def _on_login_successful(self, profile: Profile, vault: Vault) -> None:
        self.main_window = MainWindow(profile, vault)
        self.main_window.show()
        if self.login_window is not None:
            self.login_window.close()
            self.login_window = None


def main() -> None:
    app = QApplication(sys.argv)
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    apply_theme(app)
    controller = AppController()  # noqa: F841 - haelt Fenster-Referenzen am Leben
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
