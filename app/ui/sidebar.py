"""Seitenleiste mit Icon+Label-Navigation statt Reitern oben (Layout-Option B).

Icons werden zur Laufzeit per QPainter gezeichnet (keine Bild-Assets noetig)
und uebernehmen die aktuelle Textfarbe des Themes, damit sie sowohl im
Hell- als auch im Dunkelmodus lesbar bleiben. Nach einem Theme-Wechsel muss
`refresh_icons()` aufgerufen werden, da die vorgerenderten Icon-Pixel sonst
die alte Farbe behalten.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

_ICON_SIZE = 22

# (interner Schluessel, Icon-Art, Anzeigename)
PAGES = [
    ("jobsuche", "search", "Jobsuche"),
    ("vorschlaege", "list", "Vorschlaege"),
    ("bewerbungen", "mail", "Bewerbungen"),
    ("profil", "user", "Profil"),
    ("einstellungen", "settings", "Einstellungen"),
]


def _draw_icon(painter: QPainter, kind: str) -> None:
    s = _ICON_SIZE
    if kind == "search":
        painter.drawEllipse(QRectF(s * 0.14, s * 0.14, s * 0.55, s * 0.55))
        painter.drawLine(int(s * 0.6), int(s * 0.6), int(s * 0.9), int(s * 0.9))
    elif kind == "list":
        for y in (s * 0.25, s * 0.5, s * 0.75):
            painter.drawLine(int(s * 0.15), int(y), int(s * 0.85), int(y))
    elif kind == "mail":
        rect = QRectF(s * 0.1, s * 0.22, s * 0.8, s * 0.56)
        painter.drawRect(rect)
        painter.drawLine(int(rect.left()), int(rect.top()), int(s * 0.5), int(s * 0.55))
        painter.drawLine(int(rect.right()), int(rect.top()), int(s * 0.5), int(s * 0.55))
    elif kind == "user":
        painter.drawEllipse(QRectF(s * 0.32, s * 0.12, s * 0.36, s * 0.36))
        painter.drawArc(QRectF(s * 0.1, s * 0.55, s * 0.8, s * 0.55), 0, 180 * 16)
    elif kind == "settings":
        for x in (s * 0.28, s * 0.5, s * 0.72):
            painter.drawLine(int(x), int(s * 0.1), int(x), int(s * 0.9))
        for x, y in ((s * 0.28, s * 0.3), (s * 0.5, s * 0.65), (s * 0.72, s * 0.4)):
            painter.drawEllipse(QRectF(x - s * 0.09, y - s * 0.09, s * 0.18, s * 0.18))
    elif kind == "theme":
        painter.drawEllipse(QRectF(s * 0.2, s * 0.2, s * 0.6, s * 0.6))


def _make_icon(kind: str, color) -> QIcon:
    pixmap = QPixmap(_ICON_SIZE, _ICON_SIZE)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(color, 1.6))
    _draw_icon(painter, kind)
    painter.end()
    return QIcon(pixmap)


class Sidebar(QWidget):
    page_changed = Signal(int)
    theme_toggle_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 20, 8, 16)
        layout.setSpacing(4)

        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, (_, kind, label) in enumerate(PAGES):
            btn = QPushButton(f"  {label}")
            btn.setObjectName("navBtn")
            btn.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.clicked.connect(lambda _checked, idx=i: self.page_changed.emit(idx))
            layout.addWidget(btn)
            self._group.addButton(btn)
            self._buttons.append(btn)
        self._buttons[0].setChecked(True)

        layout.addStretch()

        self.theme_btn = QPushButton("  Design wechseln")
        self.theme_btn.setObjectName("navBtn")
        self.theme_btn.setFlat(True)
        self.theme_btn.clicked.connect(self.theme_toggle_requested.emit)
        layout.addWidget(self.theme_btn)

        self.refresh_icons()

    def set_current(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def refresh_icons(self) -> None:
        """Zeichnet alle Icons mit der aktuell aktiven Textfarbe neu - nach
        einem Theme-Wechsel aufrufen, da vorgerenderte Icon-Pixel sonst die
        Farbe des vorherigen Themes behalten."""
        color = self.palette().color(self.foregroundRole())
        for btn, (_, kind, _label) in zip(self._buttons, PAGES):
            btn.setIcon(_make_icon(kind, color))
        self.theme_btn.setIcon(_make_icon("theme", color))
