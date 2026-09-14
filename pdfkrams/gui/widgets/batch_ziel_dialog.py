"""
DE: Kleiner Dialog, mit dem der Nutzer festlegt, wohin die Ausgabedateien
    einer Stapelverarbeitung (mehrere Dateien einzeln verarbeitet, siehe
    z. B. VerkleinernToolWidget) geschrieben werden sollen: entweder jede
    neben ihre eigene Quelldatei, oder alle zusammen in einen einzigen
    gewaehlten Zielordner -- und ob der Dateiname dabei einen Zusatz
    bekommt oder unveraendert bleibt (Letzteres ueberschreibt bei "gleicher
    Ordner" die Originaldatei).

EN: Small dialog letting the user decide where the output files of a
    batch operation (several files processed individually, see e.g.
    VerkleinernToolWidget) should be written to: either each one next to
    its own source file, or all of them together into a single chosen
    target folder -- and whether the filename gets a suffix added or
    stays unchanged (the latter overwrites the original file when
    "same folder" is chosen).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QLabel, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from pdfkrams.gui.widgets.datei_dialoge import ordner_dialog


@dataclass
class BatchZiel:
    # DE: None bedeutet "je Datei derselbe Ordner wie die Quelle".
    # EN: None means "same folder as the source, per file".
    ordner: Path | None
    suffix: str


class _BatchZielDialog(QDialog):
    def __init__(self, parent: QWidget, suffix_vorschlag: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Ziel für mehrere Dateien"))
        self._suffix_vorschlag = suffix_vorschlag
        self._gewaehlter_ordner: Path | None = None

        self._gleicher_ordner_feld = QRadioButton(self.tr("Im selben Ordner wie jede Originaldatei"))
        self._gleicher_ordner_feld.setChecked(True)
        self._eigener_ordner_feld = QRadioButton(self.tr("In diesem Ordner:"))
        self._ordner_anzeige = QLabel(self.tr("(noch keiner gewählt)"))
        self._ordner_anzeige.setStyleSheet("color: gray;")
        self._ordner_anzeige.setWordWrap(True)
        btn_ordner_waehlen = QPushButton(self.tr("Wählen …"))
        btn_ordner_waehlen.clicked.connect(self._ordner_waehlen)
        self._eigener_ordner_feld.toggled.connect(self._eigener_ordner_umschalten)

        self._zusatz_feld = QCheckBox(
            self.tr("Namen ergänzen um „{0}“").format(suffix_vorschlag)
        )
        self._zusatz_feld.setChecked(True)
        self._zusatz_feld.toggled.connect(self._warnung_aktualisieren)
        self._gleicher_ordner_feld.toggled.connect(self._warnung_aktualisieren)

        self._warnung = QLabel()
        self._warnung.setWordWrap(True)
        self._warnung.setStyleSheet("color: #b00;")

        knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        knoepfe.accepted.connect(self._pruefen_und_akzeptieren)
        knoepfe.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._gleicher_ordner_feld)
        layout.addWidget(self._eigener_ordner_feld)
        layout.addWidget(self._ordner_anzeige)
        layout.addWidget(btn_ordner_waehlen)
        layout.addWidget(self._zusatz_feld)
        layout.addWidget(self._warnung)
        layout.addWidget(knoepfe)
        self._warnung_aktualisieren()

    def _eigener_ordner_umschalten(self, an: bool) -> None:
        if an and self._gewaehlter_ordner is None:
            self._ordner_waehlen()

    def _ordner_waehlen(self) -> None:
        ordner = ordner_dialog(self, self.tr("Zielordner wählen"))
        if ordner is None:
            if self._gewaehlter_ordner is None:
                self._gleicher_ordner_feld.setChecked(True)
            return
        self._gewaehlter_ordner = ordner
        self._ordner_anzeige.setText(str(ordner))
        self._eigener_ordner_feld.setChecked(True)

    def _warnung_aktualisieren(self) -> None:
        # DE: "Gleicher Ordner" + kein Namenszusatz = derselbe Pfad wie die
        #     Quelle -- das ueberschreibt die Originaldatei.
        # EN: "Same folder" + no name suffix = the same path as the source
        #     -- that overwrites the original file.
        if self._gleicher_ordner_feld.isChecked() and not self._zusatz_feld.isChecked():
            self._warnung.setText(
                self.tr("Achtung: Ohne Namenszusatz im selben Ordner werden die "
                       "Originaldateien überschrieben.")
            )
        else:
            self._warnung.setText("")

    def _pruefen_und_akzeptieren(self) -> None:
        if self._eigener_ordner_feld.isChecked() and self._gewaehlter_ordner is None:
            self._ordner_waehlen()
            if self._gewaehlter_ordner is None:
                return
        self.accept()

    def ergebnis(self) -> BatchZiel:
        ordner = self._gewaehlter_ordner if self._eigener_ordner_feld.isChecked() else None
        suffix = self._suffix_vorschlag if self._zusatz_feld.isChecked() else ""
        return BatchZiel(ordner=ordner, suffix=suffix)


def batch_ziel_dialog(parent: QWidget, suffix_vorschlag: str) -> BatchZiel | None:
    """DE: Zeigt den Dialog und liefert die Wahl des Nutzers, oder None bei Abbruch.
    EN: Shows the dialog and returns the user's choice, or None if cancelled."""
    dialog = _BatchZielDialog(parent, suffix_vorschlag)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.ergebnis()
