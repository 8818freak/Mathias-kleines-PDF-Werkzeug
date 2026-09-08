"""
DE: Dialog zum Umbenennen von Dateien in einem Ordner auf der Festplatte --
    unabhaengig von der gemeinsamen Dateiliste der App. Zeigt immer erst
    eine Vorschau (alter Name -> neuer Name), bevor tatsaechlich etwas auf
    der Platte veraendert wird, und prueft vorher auf Namenskollisionen mit
    bereits vorhandenen Dateien.

EN: Dialog for renaming files in a folder on disk -- independent of the
    app's shared file list. Always shows a preview first (old name -> new
    name) before actually changing anything on disk, and checks beforehand
    for name collisions with files that already exist.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.datei_umbenennen import (
    NACH_DATUM,
    NACH_NAME,
    dateien_sammeln,
    kollisionen,
    plan_ausfuehren,
    sortieren,
    umbenennungsplan,
)

_SORTIERUNG_ANZEIGE = {
    "Datum (Aufnahme-/Erstellungszeit)": NACH_DATUM,
    "Name (natürliche Sortierung)": NACH_NAME,
}


class _UmbenennenDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dateien auf der Platte umbenennen")
        self.resize(700, 600)
        self._plan = []

        self._ordner_feld = QLineEdit()
        self._ordner_feld.setReadOnly(True)
        btn_ordner = QPushButton("Wählen …")
        btn_ordner.clicked.connect(self._ordner_waehlen)
        ordner_zeile = QHBoxLayout()
        ordner_zeile.addWidget(self._ordner_feld)
        ordner_zeile.addWidget(btn_ordner)

        self._sortierung_feld = QComboBox()
        self._sortierung_feld.addItems(_SORTIERUNG_ANZEIGE.keys())

        self._basis_feld = QLineEdit()
        self._basis_feld.setPlaceholderText("optional, z. B. SEL_UNIMAT4070")

        self._start_feld = QSpinBox()
        self._start_feld.setRange(0, 999999)
        self._start_feld.setValue(1)

        self._stellen_feld = QSpinBox()
        self._stellen_feld.setRange(1, 8)
        self._stellen_feld.setValue(4)

        self._an_ort_feld = QCheckBox("An Ort und Stelle umbenennen")
        self._an_ort_feld.setChecked(True)
        self._an_ort_feld.toggled.connect(self._an_ort_umgeschaltet)

        self._zielordner_feld = QLineEdit()
        self._zielordner_feld.setReadOnly(True)
        self._zielordner_feld.setEnabled(False)
        self._btn_zielordner = QPushButton("Zielordner wählen …")
        self._btn_zielordner.setEnabled(False)
        self._btn_zielordner.clicked.connect(self._zielordner_waehlen)
        zielordner_zeile = QHBoxLayout()
        zielordner_zeile.addWidget(self._zielordner_feld)
        zielordner_zeile.addWidget(self._btn_zielordner)

        self._kopieren_feld = QCheckBox("Kopieren statt verschieben")

        formular = QFormLayout()
        formular.addRow("Ordner:", ordner_zeile)
        formular.addRow("Sortierung:", self._sortierung_feld)
        formular.addRow("Basisname:", self._basis_feld)
        formular.addRow("Startnummer:", self._start_feld)
        formular.addRow("Stellen:", self._stellen_feld)
        formular.addRow(self._an_ort_feld)
        formular.addRow("Zielordner:", zielordner_zeile)
        formular.addRow(self._kopieren_feld)

        btn_vorschau = QPushButton("Vorschau aktualisieren")
        btn_vorschau.clicked.connect(self._vorschau_aktualisieren)

        self._vorschau_liste = QListWidget()

        self._hinweis = QLabel(
            "Zuerst Ordner wählen und „Vorschau aktualisieren“ -- erst danach lässt "
            "sich tatsächlich umbenennen. Es wird nichts überschrieben; bei "
            "Namenskollisionen wird vorher gewarnt."
        )
        self._hinweis.setWordWrap(True)

        knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._btn_ausfuehren = knoepfe.addButton("Jetzt umbenennen", QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_ausfuehren.setEnabled(False)
        knoepfe.rejected.connect(self.reject)
        self._btn_ausfuehren.clicked.connect(self._ausfuehren)

        layout = QVBoxLayout(self)
        layout.addWidget(self._hinweis)
        layout.addLayout(formular)
        layout.addWidget(btn_vorschau)
        layout.addWidget(self._vorschau_liste, 1)
        layout.addWidget(knoepfe)

    def _an_ort_umgeschaltet(self, an: bool) -> None:
        self._zielordner_feld.setEnabled(not an)
        self._btn_zielordner.setEnabled(not an)
        if an:
            self._zielordner_feld.clear()

    def _ordner_waehlen(self) -> None:
        ordner = QFileDialog.getExistingDirectory(self, "Ordner wählen")
        if ordner:
            self._ordner_feld.setText(ordner)
            self._plan = []
            self._btn_ausfuehren.setEnabled(False)
            self._vorschau_liste.clear()

    def _zielordner_waehlen(self) -> None:
        ordner = QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if ordner:
            self._zielordner_feld.setText(ordner)

    def _vorschau_aktualisieren(self) -> None:
        self._plan = []
        self._btn_ausfuehren.setEnabled(False)
        self._vorschau_liste.clear()

        if not self._ordner_feld.text():
            QMessageBox.information(self, "Kein Ordner", "Bitte zuerst einen Ordner wählen.")
            return

        ordner = Path(self._ordner_feld.text())
        dateien = dateien_sammeln(ordner)
        if not dateien:
            QMessageBox.information(self, "Keine Dateien", "Keine passenden Dateien in diesem Ordner gefunden.")
            return

        art = _SORTIERUNG_ANZEIGE[self._sortierung_feld.currentText()]
        sortiert = [f for f, _quelle in sortieren(dateien, art)]

        zielordner = None if self._an_ort_feld.isChecked() else (
            Path(self._zielordner_feld.text()) if self._zielordner_feld.text() else None
        )
        self._plan = umbenennungsplan(
            sortiert, self._basis_feld.text().strip(), self._start_feld.value(),
            self._stellen_feld.value(), zielordner,
        )

        for eintrag in self._plan:
            self._vorschau_liste.addItem(f"{eintrag.alt.name}  →  {eintrag.neu.name}")

        self._btn_ausfuehren.setEnabled(True)

    def _ausfuehren(self) -> None:
        if not self._plan:
            return
        ueberschneidungen = kollisionen(self._plan)
        if ueberschneidungen:
            QMessageBox.warning(
                self, "Namenskollision",
                "Diese Zieldateien existieren bereits und würden überschrieben "
                "werden -- abgebrochen, bitte Startnummer/Basisname anpassen:\n"
                + "\n".join(p.name for p in ueberschneidungen[:10]),
            )
            return

        aktion = "kopiert" if self._kopieren_feld.isChecked() else "umbenannt/verschoben"
        antwort = QMessageBox.question(
            self, "Wirklich umbenennen?",
            f"{len(self._plan)} Dateien werden jetzt {aktion}. Das lässt sich nicht "
            f"rückgängig machen. Fortfahren?",
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return

        try:
            plan_ausfuehren(self._plan, self._kopieren_feld.isChecked())
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, "Fehlgeschlagen", str(exc))
            return

        QMessageBox.information(self, "Fertig", f"{len(self._plan)} Dateien {aktion}.")
        self.accept()


def umbenennen_dialog_oeffnen(parent: QWidget) -> None:
    """DE: Den Umbenennen-Dialog anzeigen.
    EN: Show the rename dialog."""
    _UmbenennenDialog(parent).exec()
