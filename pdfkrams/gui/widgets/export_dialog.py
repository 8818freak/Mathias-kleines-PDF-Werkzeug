"""
DE: Dialog zum Abfragen der Einstellungen fuer den Export als einzelne,
    durchnummerierte Dateien (Format, optionaler Basisname, Startnummer,
    Stellenzahl) plus die Wahl des Zielordners. Als eigene Funktion gebaut,
    damit nicht nur das Teilen-Werkzeug, sondern auch kuenftige Werkzeuge
    diese Abfrage wiederverwenden koennen.

EN: Dialog for asking the settings for exporting as individual, sequentially
    numbered files (format, optional base name, start number, digit count)
    plus choosing the target folder. Built as a standalone function so not
    only the split tool but future tools too can reuse this prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

# DE: Anzeigename -> Dateiendung. EN: Display name -> file extension.
_FORMATE = {"PDF (eine Seite je Datei)": ".pdf", "JPEG": ".jpg", "TIFF": ".tif", "BMP": ".bmp"}


@dataclass
class EinzelExportEinstellungen:
    zielordner: Path
    endung: str
    basis: str
    start: int
    stellen: int


class _EinstellungenDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Als einzelne Dateien exportieren")

        self._format_feld = QComboBox()
        self._format_feld.addItems(_FORMATE.keys())

        self._basis_feld = QLineEdit()
        self._basis_feld.setPlaceholderText("optional, z. B. Anleitung")

        self._start_feld = QSpinBox()
        self._start_feld.setRange(0, 999999)
        self._start_feld.setValue(1)

        self._stellen_feld = QSpinBox()
        self._stellen_feld.setRange(1, 8)
        self._stellen_feld.setValue(4)

        formular = QFormLayout()
        formular.addRow("Format:", self._format_feld)
        formular.addRow("Basisname:", self._basis_feld)
        formular.addRow("Startnummer:", self._start_feld)
        formular.addRow("Stellen:", self._stellen_feld)

        knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        layout = formular
        self.setLayout(layout)
        formular.addRow(knoepfe)

    def endung(self) -> str:
        return _FORMATE[self._format_feld.currentText()]

    def basis(self) -> str:
        return self._basis_feld.text().strip()

    def start(self) -> int:
        return self._start_feld.value()

    def stellen(self) -> int:
        return self._stellen_feld.value()


def einzelexport_abfragen(parent: QWidget) -> EinzelExportEinstellungen | None:
    """
    DE: Fragt Format/Basisname/Startnummer/Stellenzahl und anschliessend den
        Zielordner ab. Liefert None, wenn an irgendeiner Stelle abgebrochen wurde.

    EN: Asks for format/base name/start number/digit count and then the
        target folder. Returns None if cancelled at any point.
    """
    dialog = _EinstellungenDialog(parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    zielordner = QFileDialog.getExistingDirectory(parent, "Zielordner wählen")
    if not zielordner:
        return None

    return EinzelExportEinstellungen(
        zielordner=Path(zielordner),
        endung=dialog.endung(),
        basis=dialog.basis(),
        start=dialog.start(),
        stellen=dialog.stellen(),
    )
