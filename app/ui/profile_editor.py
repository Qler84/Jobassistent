"""Formular fuer Profildaten (Qualifikationen/Erfahrungen/Skills) sowie die
verschluesselt gespeicherten Zugangsdaten (SMTP/IMAP/Anthropic-Key)."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_CLAUDE_MODEL, anlagen_dir
from app.core.ba_jobsuche import ARBEITSZEIT_CODES
from app.core.crypto import Vault
from app.core.email_smtp import SmtpConfig
from app.core.profile import Ausbildung, Erfahrung, Profile, ProfileManager, Sprache
from app.ui.widgets import SimpleFormDialog, StringListEditor
from app.workers.profile_import_worker import ProfileImportWorker
from app.workers.smtp_test_worker import SmtpTestWorker


class ProfileEditor(QWidget):
    def __init__(self, profile: Profile, vault: Vault, manager: ProfileManager, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile
        self.vault = vault
        self.manager = manager

        self._berufserfahrung: list[Erfahrung] = list(profile.berufserfahrung)
        self._ausbildung: list[Ausbildung] = list(profile.ausbildung)
        self._sprachen: list[Sprache] = list(profile.sprachen)
        self._anlagen: list[str] = list(profile.anlagen)
        self.import_worker: ProfileImportWorker | None = None
        self.smtp_test_worker: SmtpTestWorker | None = None

        outer = QVBoxLayout(self)

        import_row = QHBoxLayout()
        self.import_btn = QPushButton("Aus Lebenslauf/Zeugnissen importieren (Claude)")
        self.import_btn.clicked.connect(self._on_import_documents)
        self.reset_btn = QPushButton("Profildaten zuruecksetzen")
        self.reset_btn.clicked.connect(self._on_reset_profile)
        import_row.addWidget(self.import_btn)
        import_row.addWidget(self.reset_btn)
        outer.addLayout(import_row)

        self.import_status_label = QLabel(
            "Fuellt das Formular unten anhand hochgeladener PDFs vor - bitte danach pruefen "
            "und bei Bedarf korrigieren, bevor du speicherst."
        )
        self.import_status_label.setWordWrap(True)
        outer.addWidget(self.import_status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)

        layout.addWidget(self._build_persoenlich_group())
        layout.addWidget(self._build_wunschposition_group())
        layout.addWidget(self._build_erfahrung_group())
        layout.addWidget(self._build_ausbildung_group())
        layout.addWidget(self._build_skills_group())
        layout.addWidget(self._build_anlagen_group())
        layout.addWidget(self._build_anschreiben_group())
        layout.addWidget(self._build_zugangsdaten_group())
        layout.addStretch()

        outer.addWidget(scroll)

        save_btn = QPushButton("Profil speichern")
        save_btn.clicked.connect(self._on_save)
        outer.addWidget(save_btn)

        self._load_into_form()

    # --- Aufbau -------------------------------------------------------

    def _build_persoenlich_group(self) -> QGroupBox:
        box = QGroupBox("Persoenliche Angaben (fuer den Absenderblock im Anschreiben)")
        form = QFormLayout(box)
        self.name_input = QLineEdit()
        self.adresse_input = QTextEdit()
        self.adresse_input.setFixedHeight(60)
        self.telefon_input = QLineEdit()
        self.email_input = QLineEdit()
        form.addRow("Name:", self.name_input)
        form.addRow("Adresse:", self.adresse_input)
        form.addRow("Telefon:", self.telefon_input)
        form.addRow("E-Mail:", self.email_input)
        return box

    def _build_wunschposition_group(self) -> QGroupBox:
        box = QGroupBox("Wunschposition")
        layout = QVBoxLayout(box)

        layout.addWidget(QLabel("Gesuchte Jobtitel (fuer Suche & Matching):"))
        self.wunschjobtitel_editor = StringListEditor(placeholder="z.B. Softwareentwickler")
        layout.addWidget(self.wunschjobtitel_editor)

        form = QFormLayout()
        self.wunschort_input = QLineEdit()
        self.umkreis_input = QSpinBox()
        self.umkreis_input.setRange(0, 200)
        self.umkreis_input.setSuffix(" km")
        self.arbeitszeit_input = QComboBox()
        self.arbeitszeit_input.addItems(list(ARBEITSZEIT_CODES.keys()))
        form.addRow("Wunschort (PLZ/Ort):", self.wunschort_input)
        form.addRow("Suchradius:", self.umkreis_input)
        form.addRow("Arbeitszeit:", self.arbeitszeit_input)
        layout.addLayout(form)
        return box

    def _build_erfahrung_group(self) -> QGroupBox:
        box = QGroupBox("Berufserfahrung (per Drag & Drop sortierbar)")
        layout = QVBoxLayout(box)
        self.erfahrung_list = QListWidget()
        self.erfahrung_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.erfahrung_list.model().rowsMoved.connect(self._sync_erfahrung_order)
        layout.addWidget(self.erfahrung_list)
        row = QHBoxLayout()
        add_btn = QPushButton("Hinzufuegen")
        remove_btn = QPushButton("Entfernen")
        add_btn.clicked.connect(self._add_erfahrung)
        remove_btn.clicked.connect(self._remove_erfahrung)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)
        layout.addLayout(row)
        return box

    def _build_ausbildung_group(self) -> QGroupBox:
        box = QGroupBox("Ausbildung (per Drag & Drop sortierbar)")
        layout = QVBoxLayout(box)
        self.ausbildung_list = QListWidget()
        self.ausbildung_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.ausbildung_list.model().rowsMoved.connect(self._sync_ausbildung_order)
        layout.addWidget(self.ausbildung_list)
        row = QHBoxLayout()
        add_btn = QPushButton("Hinzufuegen")
        remove_btn = QPushButton("Entfernen")
        add_btn.clicked.connect(self._add_ausbildung)
        remove_btn.clicked.connect(self._remove_ausbildung)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)
        layout.addLayout(row)
        return box

    def _build_skills_group(self) -> QGroupBox:
        box = QGroupBox("Skills, Sprachen & Zertifikate")
        layout = QVBoxLayout(box)

        layout.addWidget(QLabel("Skills:"))
        self.skills_editor = StringListEditor(placeholder="z.B. Python")
        layout.addWidget(self.skills_editor)

        layout.addWidget(QLabel("Sprachen (per Drag & Drop sortierbar):"))
        self.sprachen_list = QListWidget()
        self.sprachen_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.sprachen_list.model().rowsMoved.connect(self._sync_sprachen_order)
        layout.addWidget(self.sprachen_list)
        row = QHBoxLayout()
        add_btn = QPushButton("Hinzufuegen")
        remove_btn = QPushButton("Entfernen")
        add_btn.clicked.connect(self._add_sprache)
        remove_btn.clicked.connect(self._remove_sprache)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)
        layout.addLayout(row)

        layout.addWidget(QLabel("Zertifikate:"))
        self.zertifikate_editor = StringListEditor(placeholder="z.B. AWS Certified Developer")
        layout.addWidget(self.zertifikate_editor)

        return box

    def _build_anlagen_group(self) -> QGroupBox:
        box = QGroupBox("Anlagen (werden automatisch an jede versendete Bewerbung angehaengt)")
        layout = QVBoxLayout(box)
        self.anlagen_list = QListWidget()
        layout.addWidget(self.anlagen_list)
        row = QHBoxLayout()
        add_btn = QPushButton("Datei hinzufuegen")
        remove_btn = QPushButton("Entfernen")
        add_btn.clicked.connect(self._add_anlage)
        remove_btn.clicked.connect(self._remove_anlage)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)
        layout.addLayout(row)
        hinweis = QLabel(
            "Z.B. Zeugnisse, Zertifikate, Arbeitsproben. Diese Dateien werden zusaetzlich zum "
            "generierten Anschreiben-PDF an jede E-Mail angehaengt, die du im Tab 'Bewerbungen' "
            "versendest."
        )
        hinweis.setWordWrap(True)
        layout.addWidget(hinweis)
        return box

    def _build_anschreiben_group(self) -> QGroupBox:
        box = QGroupBox("Anschreiben-Anpassung")
        layout = QVBoxLayout(box)
        layout.addWidget(
            QLabel(
                "Zusaetzliche Anweisungen fuer die Anschreiben-Generierung (z.B. gewuenschter "
                "Ton, Dinge die betont/vermieden werden sollen). Werden bei jeder Generierung "
                "an Claude mitgegeben:"
            )
        )
        self.cover_letter_hinweise_input = QTextEdit()
        self.cover_letter_hinweise_input.setPlaceholderText(
            "z.B. 'Betone meine Remote-Erfahrung.' oder 'Etwas lockerer, weniger foermlich.'"
        )
        self.cover_letter_hinweise_input.setFixedHeight(80)
        layout.addWidget(self.cover_letter_hinweise_input)
        return box

    def _build_zugangsdaten_group(self) -> QGroupBox:
        box = QGroupBox("Zugangsdaten (verschluesselt mit deinem Master-Passwort gespeichert)")
        form = QFormLayout(box)

        self.anthropic_key_input = QLineEdit()
        self.anthropic_key_input.setEchoMode(QLineEdit.Password)
        form.addRow("Anthropic-API-Key:", self.anthropic_key_input)

        self.smtp_host_input = QLineEdit()
        self.smtp_port_input = QSpinBox()
        self.smtp_port_input.setRange(1, 65535)
        self.smtp_port_input.setValue(465)
        self.smtp_user_input = QLineEdit()
        self.smtp_password_input = QLineEdit()
        self.smtp_password_input.setEchoMode(QLineEdit.Password)
        form.addRow("SMTP-Server:", self.smtp_host_input)
        form.addRow("SMTP-Port:", self.smtp_port_input)
        form.addRow("E-Mail-Adresse:", self.smtp_user_input)
        form.addRow("E-Mail-Passwort:", self.smtp_password_input)

        smtp_port_hinweis = QLabel(
            "Port 465 = SSL, jeder andere Port (z.B. 587) = STARTTLS - wird automatisch "
            "anhand des Ports erkannt."
        )
        smtp_port_hinweis.setWordWrap(True)

        hinweis = QLabel(
            "Empfehlung: Verwende ein App-Passwort/Zugangspasswort fuer Mailprogramme deines "
            "E-Mail-Anbieters statt deines Hauptpassworts (z.B. bei web.de/GMX unter "
            "Einstellungen > Sicherheit erstellbar). Bei web.de/GMX muss der POP3/IMAP-Zugriff "
            "zusaetzlich einmalig in den Einstellungen aktiviert werden, sonst schlaegt der "
            "Login fehl."
        )
        hinweis.setWordWrap(True)
        hinweis.setStyleSheet("color: #e0a030;")
        form.addRow(smtp_port_hinweis)
        form.addRow(hinweis)

        self.smtp_test_btn = QPushButton("SMTP-Verbindung testen")
        self.smtp_test_btn.clicked.connect(self._on_test_smtp)
        self.smtp_test_status_label = QLabel("")
        self.smtp_test_status_label.setWordWrap(True)
        form.addRow(self.smtp_test_btn)
        form.addRow(self.smtp_test_status_label)

        self.imap_host_input = QLineEdit()
        self.imap_port_input = QSpinBox()
        self.imap_port_input.setRange(1, 65535)
        self.imap_port_input.setValue(993)
        form.addRow("IMAP-Server (fuer Status-Tracking):", self.imap_host_input)
        form.addRow("IMAP-Port:", self.imap_port_input)
        imap_hinweis = QLabel(
            "Fuer den IMAP-Abruf werden dieselbe E-Mail-Adresse und dasselbe (App-)Passwort "
            "wie oben bei SMTP verwendet."
        )
        imap_hinweis.setWordWrap(True)
        form.addRow(imap_hinweis)

        return box

    # --- PDF-Import (Lebenslauf/Zeugnisse) --------------------------------

    def _on_import_documents(self) -> None:
        api_key = self.vault.get("anthropic_api_key", "")
        if not api_key:
            QMessageBox.warning(
                self,
                "Kein API-Key",
                "Bitte hinterlege zuerst deinen Anthropic-API-Key im Bereich 'Zugangsdaten' "
                "weiter unten.",
            )
            return

        files, _ = QFileDialog.getOpenFileNames(
            self, "Lebenslauf/Zeugnisse auswaehlen", "", "PDF-Dateien (*.pdf)"
        )
        if not files:
            return

        self.import_btn.setEnabled(False)
        self.import_status_label.setText("Dokumente werden analysiert...")

        model = self.vault.get("claude_model", DEFAULT_CLAUDE_MODEL)
        self.import_worker = ProfileImportWorker(
            api_key=api_key, pdf_paths=[Path(f) for f in files], model=model
        )
        self.import_worker.finished_ok.connect(self._on_import_done)
        self.import_worker.failed.connect(self._on_import_failed)
        self.import_worker.start()

    def _on_import_done(self, data: dict) -> None:
        self.import_btn.setEnabled(True)
        self.import_status_label.setText(
            "Formular wurde vorausgefuellt - bitte alle Angaben pruefen und bei Bedarf "
            "korrigieren, bevor du unten auf 'Profil speichern' klickst."
        )
        self._apply_imported_data(data)

    def _on_import_failed(self, message: str) -> None:
        self.import_btn.setEnabled(True)
        self.import_status_label.setText("")
        QMessageBox.critical(self, "Import fehlgeschlagen", message)

    def _apply_imported_data(self, data: dict) -> None:
        self.name_input.setText(data.get("name", ""))
        self.adresse_input.setPlainText(data.get("adresse", ""))
        self.telefon_input.setText(data.get("telefon", ""))
        self.email_input.setText(data.get("email", ""))

        self.wunschjobtitel_editor.set_values(
            [t for t in data.get("wunschjobtitel", []) if isinstance(t, str)]
        )

        self._berufserfahrung = [
            Erfahrung(
                firma=e.get("firma", ""),
                position=e.get("position", ""),
                zeitraum=e.get("zeitraum", ""),
                beschreibung=e.get("beschreibung", ""),
            )
            for e in data.get("berufserfahrung", [])
            if isinstance(e, dict)
        ]
        self._refresh_erfahrung_list()

        self._ausbildung = [
            Ausbildung(
                institution=a.get("institution", ""),
                abschluss=a.get("abschluss", ""),
                zeitraum=a.get("zeitraum", ""),
            )
            for a in data.get("ausbildung", [])
            if isinstance(a, dict)
        ]
        self._refresh_ausbildung_list()

        self._sprachen = [
            Sprache(sprache=s.get("sprache", ""), niveau=s.get("niveau", ""))
            for s in data.get("sprachen", [])
            if isinstance(s, dict)
        ]
        self._refresh_sprachen_list()

        self.skills_editor.set_values([s for s in data.get("skills", []) if isinstance(s, str)])
        self.zertifikate_editor.set_values(
            [z for z in data.get("zertifikate", []) if isinstance(z, str)]
        )

    # --- SMTP-Verbindungstest -----------------------------------------

    def _on_test_smtp(self) -> None:
        host = self.smtp_host_input.text().strip()
        user = self.smtp_user_input.text().strip()
        password = self.smtp_password_input.text()
        if not host or not user or not password:
            QMessageBox.warning(
                self,
                "Angaben fehlen",
                "Bitte SMTP-Server, E-Mail-Adresse und Passwort ausfuellen, bevor du testest.",
            )
            return

        port = self.smtp_port_input.value()
        config = SmtpConfig(host=host, port=port, user=user, password=password, use_ssl=(port == 465))

        self.smtp_test_btn.setEnabled(False)
        self.smtp_test_status_label.setText("Verbindung wird getestet...")
        self.smtp_test_status_label.setStyleSheet("")

        self.smtp_test_worker = SmtpTestWorker(config)
        self.smtp_test_worker.finished_ok.connect(self._on_smtp_test_ok)
        self.smtp_test_worker.failed.connect(self._on_smtp_test_failed)
        self.smtp_test_worker.start()

    def _on_smtp_test_ok(self) -> None:
        self.smtp_test_btn.setEnabled(True)
        self.smtp_test_status_label.setStyleSheet("color: #4caf50;")
        self.smtp_test_status_label.setText("Verbindung erfolgreich - Server und Zugangsdaten sind korrekt.")

    def _on_smtp_test_failed(self, message: str) -> None:
        self.smtp_test_btn.setEnabled(True)
        self.smtp_test_status_label.setStyleSheet("color: #e05050;")
        self.smtp_test_status_label.setText(message)

    # --- Daten laden/speichern -----------------------------------------

    def _load_into_form(self) -> None:
        p = self.profile
        self.name_input.setText(p.name)
        self.adresse_input.setPlainText(p.adresse)
        self.telefon_input.setText(p.telefon)
        self.email_input.setText(p.email)

        self.wunschjobtitel_editor.set_values(p.wunschjobtitel)
        self.wunschort_input.setText(p.wunschort)
        self.umkreis_input.setValue(p.umkreis_km)
        code_to_label = {v: k for k, v in ARBEITSZEIT_CODES.items()}
        self.arbeitszeit_input.setCurrentText(code_to_label.get(p.arbeitszeit, "Vollzeit"))

        self._refresh_erfahrung_list()
        self._refresh_ausbildung_list()
        self._refresh_sprachen_list()

        self.skills_editor.set_values(p.skills)
        self.zertifikate_editor.set_values(p.zertifikate)

        self._anlagen = list(p.anlagen)
        self._refresh_anlagen_list()
        self.cover_letter_hinweise_input.setPlainText(p.cover_letter_hinweise)

        self.anthropic_key_input.setText(self.vault.get("anthropic_api_key", ""))
        self.smtp_host_input.setText(self.vault.get("smtp_host", ""))
        self.smtp_port_input.setValue(self.vault.get("smtp_port", 465))
        self.smtp_user_input.setText(self.vault.get("smtp_user", ""))
        self.smtp_password_input.setText(self.vault.get("smtp_password", ""))
        self.imap_host_input.setText(self.vault.get("imap_host", ""))
        self.imap_port_input.setValue(self.vault.get("imap_port", 993))

    def _on_save(self) -> None:
        p = self.profile
        p.name = self.name_input.text().strip()
        p.adresse = self.adresse_input.toPlainText().strip()
        p.telefon = self.telefon_input.text().strip()
        p.email = self.email_input.text().strip()

        p.wunschjobtitel = self.wunschjobtitel_editor.values()
        p.wunschort = self.wunschort_input.text().strip()
        p.umkreis_km = self.umkreis_input.value()
        p.arbeitszeit = ARBEITSZEIT_CODES[self.arbeitszeit_input.currentText()]

        p.berufserfahrung = list(self._berufserfahrung)
        p.ausbildung = list(self._ausbildung)
        p.sprachen = list(self._sprachen)
        p.skills = self.skills_editor.values()
        p.zertifikate = self.zertifikate_editor.values()

        p.anlagen = list(self._anlagen)
        p.cover_letter_hinweise = self.cover_letter_hinweise_input.toPlainText().strip()

        self.manager.save_profile(p)

        self.vault.set("anthropic_api_key", self.anthropic_key_input.text().strip())
        self.vault.set("smtp_host", self.smtp_host_input.text().strip())
        self.vault.set("smtp_port", self.smtp_port_input.value())
        self.vault.set("smtp_user", self.smtp_user_input.text().strip())
        self.vault.set("smtp_password", self.smtp_password_input.text())
        self.vault.set("imap_host", self.imap_host_input.text().strip())
        self.vault.set("imap_port", self.imap_port_input.value())
        self.vault.save()

        QMessageBox.information(self, "Gespeichert", "Profil und Zugangsdaten wurden gespeichert.")

    # --- Berufserfahrung -------------------------------------------------

    def _refresh_erfahrung_list(self) -> None:
        self.erfahrung_list.clear()
        for e in self._berufserfahrung:
            item = QListWidgetItem(f"{e.position} bei {e.firma} ({e.zeitraum})")
            item.setData(Qt.UserRole, e)
            self.erfahrung_list.addItem(item)

    def _sync_erfahrung_order(self, *args) -> None:
        self._berufserfahrung = [
            self.erfahrung_list.item(i).data(Qt.UserRole) for i in range(self.erfahrung_list.count())
        ]

    def _add_erfahrung(self) -> None:
        dialog = SimpleFormDialog(
            "Berufserfahrung hinzufuegen",
            [
                ("firma", "Firma:", False),
                ("position", "Position:", False),
                ("zeitraum", "Zeitraum:", False),
                ("beschreibung", "Beschreibung/Taetigkeiten:", True),
            ],
            self,
        )
        if dialog.exec():
            values = dialog.values()
            self._berufserfahrung.append(Erfahrung(**values))
            self._refresh_erfahrung_list()

    def _remove_erfahrung(self) -> None:
        row = self.erfahrung_list.currentRow()
        if row >= 0:
            del self._berufserfahrung[row]
            self._refresh_erfahrung_list()

    # --- Ausbildung -------------------------------------------------

    def _refresh_ausbildung_list(self) -> None:
        self.ausbildung_list.clear()
        for a in self._ausbildung:
            item = QListWidgetItem(f"{a.abschluss}, {a.institution} ({a.zeitraum})")
            item.setData(Qt.UserRole, a)
            self.ausbildung_list.addItem(item)

    def _sync_ausbildung_order(self, *args) -> None:
        self._ausbildung = [
            self.ausbildung_list.item(i).data(Qt.UserRole) for i in range(self.ausbildung_list.count())
        ]

    def _add_ausbildung(self) -> None:
        dialog = SimpleFormDialog(
            "Ausbildung hinzufuegen",
            [
                ("institution", "Institution:", False),
                ("abschluss", "Abschluss:", False),
                ("zeitraum", "Zeitraum:", False),
            ],
            self,
        )
        if dialog.exec():
            values = dialog.values()
            self._ausbildung.append(Ausbildung(**values))
            self._refresh_ausbildung_list()

    def _remove_ausbildung(self) -> None:
        row = self.ausbildung_list.currentRow()
        if row >= 0:
            del self._ausbildung[row]
            self._refresh_ausbildung_list()

    # --- Sprachen -------------------------------------------------

    def _refresh_sprachen_list(self) -> None:
        self.sprachen_list.clear()
        for s in self._sprachen:
            item = QListWidgetItem(f"{s.sprache} ({s.niveau})")
            item.setData(Qt.UserRole, s)
            self.sprachen_list.addItem(item)

    def _sync_sprachen_order(self, *args) -> None:
        self._sprachen = [
            self.sprachen_list.item(i).data(Qt.UserRole) for i in range(self.sprachen_list.count())
        ]

    def _add_sprache(self) -> None:
        dialog = SimpleFormDialog(
            "Sprache hinzufuegen",
            [("sprache", "Sprache:", False), ("niveau", "Niveau (z.B. C1, Muttersprache):", False)],
            self,
        )
        if dialog.exec():
            values = dialog.values()
            self._sprachen.append(Sprache(**values))
            self._refresh_sprachen_list()

    def _remove_sprache(self) -> None:
        row = self.sprachen_list.currentRow()
        if row >= 0:
            del self._sprachen[row]
            self._refresh_sprachen_list()

    # --- Anlagen -------------------------------------------------

    def _refresh_anlagen_list(self) -> None:
        self.anlagen_list.clear()
        self.anlagen_list.addItems(self._anlagen)

    def _add_anlage(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Anlagen auswaehlen",
            "",
            "Dokumente (*.pdf *.docx *.doc *.jpg *.jpeg *.png);;Alle Dateien (*)",
        )
        if not files:
            return
        ziel_ordner = anlagen_dir(self.profile.slug)
        for datei in files:
            quelle = Path(datei)
            ziel = ziel_ordner / quelle.name
            if quelle.resolve() != ziel.resolve():
                shutil.copyfile(quelle, ziel)
            if quelle.name not in self._anlagen:
                self._anlagen.append(quelle.name)
        self._refresh_anlagen_list()

    def _remove_anlage(self) -> None:
        row = self.anlagen_list.currentRow()
        if row < 0:
            return
        dateiname = self._anlagen[row]
        pfad = anlagen_dir(self.profile.slug) / dateiname
        if pfad.exists():
            pfad.unlink()
        del self._anlagen[row]
        self._refresh_anlagen_list()

    # --- Profildaten zuruecksetzen -----------------------------------

    def _on_reset_profile(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Profildaten zuruecksetzen",
            "Alle Angaben im Profil-Formular (persoenliche Angaben, Wunschposition, "
            "Berufserfahrung, Ausbildung, Skills, Sprachen, Zertifikate) werden geleert.\n\n"
            "Zugangsdaten, Anlagen und Einstellungen (Match-Schwelle etc.) bleiben erhalten.\n"
            "Nichts wird sofort gespeichert - du kannst das Ergebnis noch pruefen, bevor du "
            "auf 'Profil speichern' klickst.\n\nFortfahren?",
        )
        if confirm != QMessageBox.Yes:
            return

        leer = Profile(slug=self.profile.slug, display_name=self.profile.display_name)
        self.name_input.setText(leer.name)
        self.adresse_input.setPlainText(leer.adresse)
        self.telefon_input.setText(leer.telefon)
        self.email_input.setText(leer.email)

        self.wunschjobtitel_editor.set_values(leer.wunschjobtitel)
        self.wunschort_input.setText(leer.wunschort)
        self.umkreis_input.setValue(leer.umkreis_km)
        code_to_label = {v: k for k, v in ARBEITSZEIT_CODES.items()}
        self.arbeitszeit_input.setCurrentText(code_to_label.get(leer.arbeitszeit, "Vollzeit"))

        self._berufserfahrung = []
        self._refresh_erfahrung_list()
        self._ausbildung = []
        self._refresh_ausbildung_list()
        self._sprachen = []
        self._refresh_sprachen_list()

        self.skills_editor.set_values([])
        self.zertifikate_editor.set_values([])
        self.cover_letter_hinweise_input.setPlainText("")

        QMessageBox.information(
            self,
            "Zurueckgesetzt",
            "Das Formular wurde geleert. Klicke auf 'Profil speichern', um das zu uebernehmen.",
        )
