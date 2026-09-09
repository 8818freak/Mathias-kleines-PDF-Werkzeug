"""
DE: Werkzeug "PDF erstellen": exportiert die gemeinsame Seitenliste (siehe
    DateiListenPanel) als eine einzelne PDF-Datei. Reihenfolge, Hinzufuegen
    und Entfernen von Dateien passiert zentral im Datei-Panel, nicht hier.

EN: "Create PDF" tool: exports the shared page list (see DateiListenPanel)
    as a single PDF file. Ordering, adding, and removing files happens
    centrally in the file panel, not here.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from pdfkrams.core.combine import export_pdf
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget


class CombineToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zusammenbauen einer PDF aus der gemeinsamen Seitenliste.
    EN: GUI page for assembling a PDF from the shared page list.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        hinweis = QLabel(
            self.tr("Baut aus der Dateiliste links eine einzelne PDF-Datei, in der dort "
                   "gezeigten Reihenfolge (inklusive bereits vorgenommener Drehungen, "
                   "Spiegelungen und Teilungen).")
        )
        hinweis.setWordWrap(True)

        self._btn_export = QPushButton(self.tr("Als PDF exportieren …"))
        self._btn_export.clicked.connect(self._exportieren)
        self._btn_export.setEnabled(self.liste.count() > 0)
        self.liste.geaendert.connect(
            lambda: self._btn_export.setEnabled(self.liste.count() > 0)
        )

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addStretch(1)
        layout.addWidget(self._btn_export)

    def _exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, self.tr("PDF speichern unter"), self.tr("zusammengefuegt.pdf"), self.tr("PDF-Datei (*.pdf)")
        )
        if not ziel:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, self.tr("PDF wird erstellt …"), len(seiten))
        try:
            export_pdf(seiten, Path(ziel), fortschritt=anzeige.callback)
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Export fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(self, self.tr("Fertig"), self.tr("PDF gespeichert unter:\n{0}").format(ziel))
