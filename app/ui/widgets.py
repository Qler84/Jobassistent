"""Wiederverwendbare kleine UI-Bausteine fuer den Profil-Editor."""
from __future__ import annotations

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def size_button_to_text(button: QPushButton, extra: int = 36) -> None:
    """Setzt eine Mindestbreite anhand der tatsaechlichen Textbreite.

    Noetig, weil QPushButton.sizeHint() unter manchen qt-material-Themes das
    QSS-Padding nicht zuverlaessig einrechnet - ohne diese explizite Breite
    wird laengerer Button-Text (z.B. "Bestaetigen") an den Raendern
    abgeschnitten statt vollstaendig angezeigt zu werden."""
    metrics = QFontMetrics(button.font())
    button.setMinimumWidth(metrics.horizontalAdvance(button.text()) + extra)


class StringListEditor(QWidget):
    """Einfache Liste von Freitext-Eintraegen (z.B. Skills, Zertifikate) mit
    Hinzufuegen/Entfernen."""

    def __init__(self, placeholder: str = "", parent=None) -> None:
        super().__init__(parent)
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        add_btn = QPushButton("Hinzufuegen")
        remove_btn = QPushButton("Entfernen")

        add_btn.clicked.connect(self._add)
        remove_btn.clicked.connect(self._remove)
        self.input.returnPressed.connect(self._add)

        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)
        layout.addLayout(row)

    def _add(self) -> None:
        text = self.input.text().strip()
        if text:
            self.list_widget.addItem(text)
            self.input.clear()

    def _remove(self) -> None:
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def values(self) -> list[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def set_values(self, values: list[str]) -> None:
        self.list_widget.clear()
        self.list_widget.addItems(values)


class SimpleFormDialog(QDialog):
    """Generischer kleiner Dialog fuer strukturierte Eintraege (z.B. eine
    Station der Berufserfahrung). `fields` ist eine Liste von (key, label,
    multiline)."""

    def __init__(self, title: str, fields: list[tuple[str, str, bool]], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._fields = fields
        self._inputs: dict[str, QWidget] = {}

        form = QFormLayout()
        for key, label, multiline in fields:
            widget = QTextEdit() if multiline else QLineEdit()
            if multiline:
                widget.setFixedHeight(70)
            self._inputs[key] = widget
            form.addRow(label, widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def set_values(self, data: dict[str, str]) -> None:
        for key, value in data.items():
            widget = self._inputs.get(key)
            if isinstance(widget, QTextEdit):
                widget.setPlainText(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(value)

    def values(self) -> dict[str, str]:
        result = {}
        for key, widget in self._inputs.items():
            result[key] = widget.toPlainText() if isinstance(widget, QTextEdit) else widget.text()
        return result
