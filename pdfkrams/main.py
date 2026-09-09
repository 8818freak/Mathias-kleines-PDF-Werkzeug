"""
DE: Einstiegspunkt der Anwendung. Laedt vor dem Aufbau des Hauptfensters
    die passende Uebersetzungsdatei fuer die eingestellte Sprache (siehe
    pdfkrams/einstellungen.py) -- fuer Deutsch (Standard) ist keine Datei
    noetig, da die Texte im Code bereits deutsch sind.

    Kuemmert sich außerdem darum, Dateien zu laden, die von außen
    uebergeben werden -- unter macOS per Finder "Oeffnen mit …"/Doppelklick
    (kommt als QFileOpenEvent, nicht als Kommandozeilenargument, siehe
    _App.event()), unter Windows per Doppelklick/Dateizuordnung (kommt als
    normales sys.argv-Argument).

EN: Application entry point. Before building the main window, loads the
    translation file matching the configured language (see
    pdfkrams/einstellungen.py) -- for German (the default) no file is
    needed, since the in-code texts are already German.

    Also takes care of loading files supplied from outside -- on macOS via
    Finder's "Open With …"/double-click (arrives as a QFileOpenEvent, not a
    command-line argument, see _App.event()), on Windows via
    double-click/file association (arrives as a plain sys.argv argument).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QTranslator
from PySide6.QtWidgets import QApplication

from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.main_window import MainWindow

_UEBERSETZUNGEN_ORDNER = Path(__file__).parent / "uebersetzungen"


class _App(QApplication):
    """DE: QApplication-Unterklasse, die macOS' QFileOpenEvent abfaengt --
        das Ereignis, mit dem der Finder eine Datei an eine (ggf. schon
        laufende) App uebergibt, statt sie als Kommandozeilenargument zu
        uebergeben. Trifft ein solches Ereignis ein, bevor das Hauptfenster
        existiert (moeglich beim Programmstart), wird der Pfad
        zwischengespeichert und erst beim Aufruf von fenster_registrieren()
        nachgeholt.
    EN: QApplication subclass that intercepts macOS' QFileOpenEvent -- the
        event Finder uses to hand a file to a (possibly already running)
        app, instead of passing it as a command-line argument. If such an
        event arrives before the main window exists (possible at program
        start), the path is buffered and only delivered once
        fenster_registrieren() is called."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self._fenster: MainWindow | None = None
        self._wartende_pfade: list[Path] = []

    def fenster_registrieren(self, fenster: MainWindow) -> None:
        self._fenster = fenster
        if self._wartende_pfade:
            fenster.dateien_oeffnen(self._wartende_pfade)
            self._wartende_pfade = []

    def event(self, event) -> bool:  # noqa: N802 (Qt-Ueberschreibung)
        if event.type() == QEvent.Type.FileOpen:
            pfad = Path(event.file())
            if self._fenster is not None:
                self._fenster.dateien_oeffnen([pfad])
            else:
                self._wartende_pfade.append(pfad)
            return True
        return super().event(event)


def main() -> None:
    app = _App(sys.argv)

    sprache = einstellungen.sprache()
    if sprache != "de":
        uebersetzer = QTranslator(app)
        if uebersetzer.load(str(_UEBERSETZUNGEN_ORDNER / f"pdfkrams_{sprache}.qm")):
            app.installTranslator(uebersetzer)

    fenster = MainWindow()
    app.fenster_registrieren(fenster)

    # DE: Unter Windows kommt eine per Doppelklick/Dateizuordnung geoeffnete
    #     Datei als normales Kommandozeilenargument an.
    # EN: On Windows, a file opened via double-click/file association
    #     arrives as a plain command-line argument.
    argv_pfade = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
    if argv_pfade:
        fenster.dateien_oeffnen(argv_pfade)

    fenster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
