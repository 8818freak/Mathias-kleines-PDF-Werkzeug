"""
DE: Werkzeug "PDF erstellen": exportiert die gemeinsame Seitenliste (siehe
    DateiListenPanel) als eine einzelne PDF-Datei. Reihenfolge, Hinzufuegen
    und Entfernen von Dateien passiert zentral im Datei-Panel, nicht hier.

EN: "Create PDF" tool: exports the shared page list (see DateiListenPanel)
    as a single PDF file. Ordering, adding, and removing files happens
    centrally in the file panel, not here.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.pdf_export import seitenliste_als_pdf_exportieren


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
        seitenliste_als_pdf_exportieren(
            self, self.liste,
            dialog_titel=self.tr("PDF speichern unter"),
            dateiname_vorschlag=self.tr("zusammengefuegt.pdf"),
            dialog_filter=self.tr("PDF-Datei (*.pdf)"),
            fortschritt_text=self.tr("PDF wird erstellt …"),
            fehler_titel=self.tr("Export fehlgeschlagen"),
            erfolg_titel=self.tr("Fertig"),
            erfolg_text_vorlage=self.tr("PDF gespeichert unter:\n{0}"),
        )
