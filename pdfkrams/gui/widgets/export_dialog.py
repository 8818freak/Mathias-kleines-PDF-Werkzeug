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

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from pdfkrams.gui.widgets.datei_dialoge import ordner_dialog

# DE: Dateiendung -> (unuebersetzter) Anzeigename. Als Dateiendung
#     verschluesselt statt als uebersetzten Anzeigetext, damit die
#     Auswahl per currentData() sprachunabhaengig funktioniert.
# EN: File extension -> (untranslated) display name. Keyed by file
#     extension rather than the translated display text, so selection
#     via currentData() works independently of the current language.
_FORMATE = {".pdf": "PDF (eine Seite je Datei)", ".jpg": "JPEG", ".tif": "TIFF", ".bmp": "BMP"}


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
        self.setWindowTitle(self.tr("Als einzelne Dateien exportieren"))
        # DE: Cmd+W schliesst dieses Fenster -- siehe die ausfuehrliche
        #     Begruendung in gui/einstellungen_dialog.py.
        # EN: Cmd+W closes this window -- see the detailed rationale in
        #     gui/einstellungen_dialog.py.
        QShortcut(QKeySequence.StandardKey.Close, self, activated=self.close)

        self._format_feld = QComboBox()
        for endung, anzeige in _FORMATE.items():
            self._format_feld.addItem(self.tr(anzeige), endung)

        self._basis_feld = QLineEdit()
        self._basis_feld.setPlaceholderText(self.tr("optional, z. B. Anleitung"))

        self._start_feld = QSpinBox()
        self._start_feld.setRange(0, 999999)
        self._start_feld.setValue(1)

        self._stellen_feld = QSpinBox()
        self._stellen_feld.setRange(1, 8)
        self._stellen_feld.setValue(4)

        formular = QFormLayout()
        formular.addRow(self.tr("Format:"), self._format_feld)
        formular.addRow(self.tr("Basisname:"), self._basis_feld)
        formular.addRow(self.tr("Startnummer:"), self._start_feld)
        formular.addRow(self.tr("Stellen:"), self._stellen_feld)

        knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)

        layout = formular
        self.setLayout(layout)
        formular.addRow(knoepfe)

    def endung(self) -> str:
        return self._format_feld.currentData()

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

    zielordner = ordner_dialog(parent, QCoreApplication.translate("ExportDialog", "Zielordner wählen"))
    if zielordner is None:
        return None

    return EinzelExportEinstellungen(
        zielordner=zielordner,
        endung=dialog.endung(),
        basis=dialog.basis(),
        start=dialog.start(),
        stellen=dialog.stellen(),
    )
