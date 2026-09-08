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

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from pdfkrams.core.document import UNTERSTUETZTE_ENDUNGEN, datei_aufschluesseln, ist_unterstuetzt
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget

# DE: Dateifilter fuer den Auswahldialog, aus den unterstuetzten Endungen gebaut.
# EN: File filter for the open dialog, built from the supported extensions.
DATEIFILTER = "Unterstützte Dateien (" + " ".join(f"*{e}" for e in sorted(UNTERSTUETZTE_ENDUNGEN)) + ")"


class DateiListenPanel(QWidget):
    """
    DE: Persistentes Panel mit der gemeinsamen Seitenliste (`self.liste`)
        plus Dateiauswahl-Dialog und Drag&Drop vom Finder. Wird einmal im
        Hauptfenster angelegt und von allen Werkzeugen gemeinsam benutzt.

    EN: Persistent panel with the shared page list (`self.liste`) plus a
        file picker dialog and drag&drop from Finder. Created once in the
        main window and used jointly by every tool.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.liste = PageListWidget(self)

        hinweis = QLabel(
            "Dateien (gilt für alle Werkzeuge -- einmal laden, nacheinander "
            "bearbeiten): per Drag&Drop hierher ziehen oder auswählen."
        )
        hinweis.setWordWrap(True)

        btn_hinzufuegen = QPushButton("Dateien hinzufügen …")
        btn_hinzufuegen.clicked.connect(self.dateien_hinzufuegen_dialog)
        btn_entfernen = QPushButton("Auswahl entfernen")
        btn_entfernen.clicked.connect(self.liste.ausgewaehlte_entfernen)
        btn_leeren = QPushButton("Liste leeren")
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
        pfade, _ = QFileDialog.getOpenFileNames(self, "Dateien auswählen", "", DATEIFILTER)
        self._pfade_verarbeiten([Path(p) for p in pfade])

    def _pfade_verarbeiten(self, pfade: list[Path]) -> None:
        """DE: Ausgewaehlte/gezogene Dateien in Seiten aufschluesseln und
        anhaengen -- als ein einziger Rueckgaengig-Schritt, egal wie viele
        Dateien es sind.
        EN: Break selected/dropped files down into pages and append them --
        as a single undo step, regardless of how many files there are."""
        if not pfade:
            return
        unbekannt = []
        anzeige = Fortschrittsanzeige(self, "Dateien werden geladen …", len(pfade))
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
                "Nicht unterstütztes Format",
                "Diese Dateien wurden übersprungen:\n" + "\n".join(unbekannt),
            )

    # -- Drag & Drop vom Finder / from Finder ------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        pfade = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self._pfade_verarbeiten(pfade)
        event.acceptProposedAction()
