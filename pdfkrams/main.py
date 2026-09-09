"""
DE: Einstiegspunkt der Anwendung. Laedt vor dem Aufbau des Hauptfensters
    die passende Uebersetzungsdatei fuer die eingestellte Sprache (siehe
    pdfkrams/einstellungen.py) -- fuer Deutsch (Standard) ist keine Datei
    noetig, da die Texte im Code bereits deutsch sind.
EN: Application entry point. Before building the main window, loads the
    translation file matching the configured language (see
    pdfkrams/einstellungen.py) -- for German (the default) no file is
    needed, since the in-code texts are already German.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTranslator
from PySide6.QtWidgets import QApplication

from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.main_window import MainWindow

_UEBERSETZUNGEN_ORDNER = Path(__file__).parent / "uebersetzungen"


def main() -> None:
    app = QApplication(sys.argv)

    sprache = einstellungen.sprache()
    if sprache != "de":
        uebersetzer = QTranslator(app)
        if uebersetzer.load(str(_UEBERSETZUNGEN_ORDNER / f"pdfkrams_{sprache}.qm")):
            app.installTranslator(uebersetzer)

    fenster = MainWindow()
    fenster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
