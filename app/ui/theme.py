"""Moderne Optik via qt-material - mit Hell-/Dunkelmodus-Umschaltung."""
from __future__ import annotations

from qt_material import apply_stylesheet

from app.config import load_ui_settings, save_ui_settings

THEMES = {
    "dark": "dark_teal.xml",
    "light": "light_blue.xml",
}
DEFAULT_MODE = "dark"

EXTRA_STYLES = """
QPushButton { border-radius: 6px; padding: 6px 14px; text-transform: none; }
QLineEdit, QTextEdit, QComboBox, QSpinBox { border-radius: 4px; padding: 4px; }
QTabWidget::pane { border-radius: 6px; }
QTableWidget { border-radius: 6px; }
QHeaderView::section { text-transform: none; }
QWidget#sidebar { border-right: 1px solid rgba(127, 127, 127, 60); }
QPushButton#navBtn {
    text-align: left;
    border: none;
    border-radius: 6px;
    padding: 10px 12px;
    font-weight: 400;
}
QPushButton#navBtn:checked {
    background-color: rgba(55, 138, 221, 45);
    font-weight: 500;
}
QPushButton#navBtn:hover:!checked { background-color: rgba(127, 127, 127, 20); }
QWidget#dashboardBar { border-bottom: 1px solid rgba(127, 127, 127, 60); }
QWidget#metricTile {
    background-color: rgba(127, 127, 127, 18);
    border-radius: 10px;
}
"""

# Nur im Hellmodus: erzwingt ein reinweisses Grundlayout (Variante A), statt
# des von qt-material vorgegebenen hellgrauen Canvas-Hintergrunds. Wird
# gezielt an die unbenannten Layout-Container gebunden (nicht an QWidget
# allgemein), damit Tabellen/Buttons/Inputs ihre eigene material-Optik
# behalten und im Dunkelmodus nichts beeinflusst wird.
LIGHT_EXTRA_STYLES = """
QMainWindow, QWidget#centralArea, QWidget#contentArea, QWidget#sidebar, QWidget#dashboardBar,
QStackedWidget, QStackedWidget > QWidget {
    background-color: #ffffff;
}
QTableWidget { background-color: #ffffff; alternate-background-color: #ffffff; }
QHeaderView::section { background-color: #f5f7fa; }
"""


def current_mode() -> str:
    mode = load_ui_settings().get("theme_mode", DEFAULT_MODE)
    return mode if mode in THEMES else DEFAULT_MODE


def apply_theme(app, mode: str | None = None) -> None:
    """Wendet das Theme an. Ohne `mode` wird die zuletzt gespeicherte Wahl
    genutzt (Standard: dunkel) - so nutzt auch das Login-Fenster vor dem
    ersten Profil-Login bereits die richtige Optik."""
    mode = mode if mode in THEMES else current_mode()
    apply_stylesheet(app, theme=THEMES[mode], extra={"density_scale": "-1"})
    extra_styles = EXTRA_STYLES + (LIGHT_EXTRA_STYLES if mode == "light" else "")
    app.setStyleSheet(app.styleSheet() + extra_styles)


def set_theme(app, mode: str) -> None:
    """Wechselt das Theme zur Laufzeit und merkt sich die Wahl dauerhaft
    (gilt fuer die ganze Installation, nicht nur das aktuelle Profil)."""
    if mode not in THEMES:
        return
    settings = load_ui_settings()
    settings["theme_mode"] = mode
    save_ui_settings(settings)
    apply_theme(app, mode)
