"""
DE: Gemeinsame Dateiliste, die fuer alle Werkzeuge gleichzeitig gilt.
    Einmal geladen, bleiben die Seiten (mit allem, was man ihnen bisher
    angetan hat -- Drehung, Spiegelung, Teilung) beim Wechsel zwischen den
    Werkzeugen erhalten, sodass sich mehrere Bearbeitungsschritte
    hintereinander anwenden lassen, ohne zwischendurch zu exportieren und
    neu zu laden.

EN: Shared file list that applies to all tools at once. Once loaded, pages
    (with everything done to them so far -- rotation, mirroring, splitting)
    stay intact when switching between tools, so several editing steps can
    be applied one after another without exporting and reloading in between.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from pdfkrams.core.document import UNTERSTUETZTE_ENDUNGEN, datei_aufschluesseln, ist_unterstuetzt
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget


def _dateifilter() -> str:
    """DE: Dateifilter fuer den Auswahldialog, aus den unterstuetzten Endungen gebaut.
    EN: File filter for the open dialog, built from the supported extensions."""
    text = QCoreApplication.translate("DateiListenPanel", "Unterstützte Dateien")
    return text + " (" + " ".join(f"*{e}" for e in sorted(UNTERSTUETZTE_ENDUNGEN)) + ")"


class DateiListenPanel(QWidget):
    """
    DE: Persistentes Panel mit der gemeinsamen Seitenliste (`self.liste`)
        plus Dateiauswahl-Dialog und Drag&Drop vom Finder. Wird einmal im
        Hauptfenster angelegt und von allen Werkzeugen gemeinsam benutzt.

    EN: Persistent panel with the shared page list (`self.liste`) plus a
        file picker dialog and drag&drop from Finder. Created once in the
        main window and used jointly by every tool.
    """

    # DE: Wird ausgeloest, wenn genau eine PDF-Datei in eine zuvor leere
    #     Liste geladen wurde -- also erkennbar "diese eine Datei geoeffnet"
    #     statt "mehrere Dateien zu etwas Neuem zusammengestellt". Das
    #     Hauptfenster nutzt das, um "Speichern" (Cmd+S) direkt in diese
    #     Datei schreiben zu lassen, statt jedes Mal nach einem Speicherort
    #     zu fragen.
    # EN: Fired when exactly one PDF file was loaded into a previously
    #     empty list -- i.e. recognizably "this one file was opened"
    #     rather than "several files assembled into something new". The
    #     main window uses this to make "Save" (Cmd+S) write straight back
    #     into that file, instead of asking for a location every time.
    einzelneDateiGeoeffnet = Signal(Path)

    # DE: Wird ausgeloest, wenn Dateien dazukommen, OHNE dass der Fall oben
    #     zutrifft (mehrere Dateien auf einmal, oder Hinzufuegen zu einer
    #     schon nicht mehr leeren Liste) -- die Liste stellt dann nicht mehr
    #     eine einzelne, unveraenderte Ausgangsdatei dar. Das Hauptfenster
    #     verwirft darauf ein zuvor gemerktes Speicherziel, damit "Speichern"
    #     nicht versehentlich die urspruengliche Datei mit zusammengefuehrten
    #     Inhalten ueberschreibt, ohne vorher zu fragen.
    # EN: Fired when files are added WITHOUT the case above applying
    #     (several files at once, or adding to an already non-empty list)
    #     -- the list no longer represents a single, unmodified source
    #     file. The main window discards any previously remembered save
    #     target so "Save" doesn't silently overwrite the original file
    #     with merged content without asking first.
    andereDateienHinzugefuegt = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.liste = PageListWidget(self)

        hinweis = QLabel(
            self.tr("Dateien (gilt für alle Werkzeuge -- einmal laden, nacheinander "
                   "bearbeiten): per Drag&Drop hierher ziehen oder auswählen.")
        )
        hinweis.setWordWrap(True)

        btn_hinzufuegen = QPushButton(self.tr("Dateien hinzufügen …"))
        btn_hinzufuegen.clicked.connect(self.dateien_hinzufuegen_dialog)
        btn_entfernen = QPushButton(self.tr("Auswahl entfernen"))
        btn_entfernen.clicked.connect(self.liste.ausgewaehlte_entfernen)
        btn_leeren = QPushButton(self.tr("Liste leeren"))
        btn_leeren.clicked.connect(self.liste.alle_entfernen)

        knopfzeile = QHBoxLayout()
        knopfzeile.addWidget(btn_hinzufuegen)
        knopfzeile.addWidget(btn_entfernen)
        knopfzeile.addWidget(btn_leeren)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addLayout(knopfzeile)
        layout.addWidget(self.liste, 1)

    def dateien_hinzufuegen_dialog(self) -> None:
        pfade, _ = QFileDialog.getOpenFileNames(self, self.tr("Dateien auswählen"), "", _dateifilter())
        self._pfade_verarbeiten([Path(p) for p in pfade])

    def _pfade_verarbeiten(self, pfade: list[Path]) -> None:
        """DE: Ausgewaehlte/gezogene Dateien in Seiten aufschluesseln und
        anhaengen -- als ein einziger Rueckgaengig-Schritt, egal wie viele
        Dateien es sind.
        EN: Break selected/dropped files down into pages and append them --
        as a single undo step, regardless of how many files there are."""
        if not pfade:
            return
        war_leer = self.liste.count() == 0
        unbekannt = []
        anzeige = Fortschrittsanzeige(self, self.tr("Dateien werden geladen …"), len(pfade))
        try:
            with self.liste.stapelverarbeitung():
                for i, pfad in enumerate(pfade, start=1):
                    if not ist_unterstuetzt(pfad):
                        unbekannt.append(pfad.name)
                    else:
                        self.liste.seiten_anhaengen(datei_aufschluesseln(pfad))
                    anzeige.callback(i, len(pfade))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()
        if unbekannt:
            QMessageBox.warning(
                self,
                self.tr("Nicht unterstütztes Format"),
                self.tr("Diese Dateien wurden übersprungen:\n{0}").format("\n".join(unbekannt)),
            )
        if war_leer and len(pfade) == 1 and not unbekannt and pfade[0].suffix.lower() == ".pdf":
            self.einzelneDateiGeoeffnet.emit(pfade[0])
        else:
            self.andereDateienHinzugefuegt.emit()

    # -- Drag & Drop vom Finder / from Finder ------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        pfade = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self._pfade_verarbeiten(pfade)
        event.acceptProposedAction()
