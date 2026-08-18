"""Hauptfenster: Seitenleiste (Navigation) + Kennzahlenleiste + Inhaltsbereich."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import ICON_PATH, db_path
from app.core.crypto import Vault
from app.core.database import Database
from app.core.profile import Profile, ProfileManager
from app.ui import theme
from app.ui.applications_view import ApplicationsView
from app.ui.dashboard_bar import DashboardBar
from app.ui.job_search_view import JobSearchView
from app.ui.profile_editor import ProfileEditor
from app.ui.settings_view import SettingsView
from app.ui.sidebar import Sidebar
from app.ui.suggestions_view import SuggestionsView


class MainWindow(QMainWindow):
    def __init__(self, profile: Profile, vault: Vault, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.manager = ProfileManager()
        self.db = Database(db_path(profile.slug))

        self.setWindowTitle(f"Job-Assistent - {profile.display_name}")
        self.setMinimumSize(1000, 700)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.suggestions_view = SuggestionsView(self.profile, self.vault, self.db)
        self.job_search_view = JobSearchView(
            self.profile, self.vault, self.db, on_search_done=self._on_data_changed
        )
        self.applications_view = ApplicationsView(self.profile, self.vault, self.db)
        self.profile_editor = ProfileEditor(self.profile, self.vault, self.manager)
        self.settings_view = SettingsView(self.profile, self.vault, self.manager)
        self.settings_view.settings_saved.connect(self._apply_imap_timer_settings)

        self.pages = QStackedWidget()
        # Reihenfolge muss zu app.ui.sidebar.PAGES passen.
        self.pages.addWidget(self.job_search_view)
        self.pages.addWidget(self.suggestions_view)
        self.pages.addWidget(self.applications_view)
        self.pages.addWidget(self.profile_editor)
        self.pages.addWidget(self.settings_view)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.sidebar.theme_toggle_requested.connect(self._on_toggle_theme)

        self.dashboard_bar = DashboardBar(self.db)

        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.dashboard_bar)
        content_layout.addWidget(self.pages)

        central = QWidget()
        central.setObjectName("centralArea")
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(content, stretch=1)
        self.setCentralWidget(central)

        self.imap_timer = QTimer(self)
        self.imap_timer.timeout.connect(self.applications_view.check_inbox)
        self._apply_imap_timer_settings()

    def _on_page_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.sidebar.set_current(index)
        if self.pages.widget(index) is self.applications_view:
            self.applications_view.refresh()
        self.dashboard_bar.refresh()

    def _on_data_changed(self) -> None:
        """Aktualisiert alle von neuen Treffern/Bewerbungen abhaengigen
        Ansichten - wird nach Suche, Job-Alert-Import etc. aufgerufen."""
        self.suggestions_view.refresh()
        self.dashboard_bar.refresh()

    def _on_toggle_theme(self) -> None:
        new_mode = "light" if theme.current_mode() == "dark" else "dark"
        app = QApplication.instance()
        theme.set_theme(app, new_mode)
        self.sidebar.refresh_icons()

    def _apply_imap_timer_settings(self) -> None:
        self.imap_timer.stop()
        enabled = bool(self.vault.get("imap_auto_check_enabled", False))
        has_credentials = bool(
            self.vault.get("imap_host") and self.vault.get("smtp_user") and self.vault.get("smtp_password")
        )
        if enabled and has_credentials:
            minutes = int(self.vault.get("imap_auto_check_minutes", 30))
            self.imap_timer.start(minutes * 60 * 1000)
