"""
DE: Werkzeug "PDF erstellen": exportiert die gemeinsame Seitenliste (siehe
    DateiListenPanel) als eine einzelne PDF-Datei. Reihenfolge, Hinzufuegen
    und Entfernen von Dateien passiert zentral im Datei-Panel, nicht hier.
    Zusaetzlich lassen sich hier nur die markierten Seiten in eine eigene
    neue Datei entnehmen -- wahlweise als Kopie (bleiben auch in der
    aktuellen Liste) oder verschoben (werden danach aus der aktuellen
    Liste entfernt).

EN: "Create PDF" tool: exports the shared page list (see DateiListenPanel)
    as a single PDF file. Ordering, adding, and removing files happens
    centrally in the file panel, not here. Additionally, just the marked
    pages can be taken out into their own new file here -- either as a
    copy (they also stay in the current list) or moved (removed from the
    current list afterward).
"""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget

from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.pdf_export import ausgewaehlte_als_pdf_exportieren, seitenliste_als_pdf_exportieren


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

        # DE: Einzelne oder mehrere Seiten aus der aktuellen Liste
        #     entnehmen (herauskopieren oder -verschieben) und in eine
        #     eigene, neue Datei packen -- z. B. um ein paar Seiten aus
        #     einem laengeren Dokument getrennt weiterzugeben.
        # EN: Take one or several pages out of the current list (copy or
        #     move them out) and pack them into their own new file -- e.g.
        #     to hand a few pages from a longer document off separately.
        auswahl_hinweis = QLabel(
            self.tr("Nur die markierten Seiten in eine neue Datei packen (in der Liste links "
                   "zuerst auswählen):")
        )
        auswahl_hinweis.setWordWrap(True)
        btn_auswahl_kopieren = QPushButton(self.tr("Markierte Seiten als neue Datei exportieren …"))
        btn_auswahl_kopieren.clicked.connect(lambda: self._auswahl_exportieren(entfernen=False))
        btn_auswahl_verschieben = QPushButton(self.tr("Markierte Seiten in neue Datei verschieben …"))
        btn_auswahl_verschieben.setToolTip(
            self.tr("Wie „… exportieren“, entfernt die markierten Seiten danach zusätzlich aus "
                   "der aktuellen Liste.")
        )
        btn_auswahl_verschieben.clicked.connect(lambda: self._auswahl_exportieren(entfernen=True))

        auswahl_gruppe = QGroupBox(self.tr("Seiten entnehmen"))
        auswahl_layout = QVBoxLayout(auswahl_gruppe)
        auswahl_layout.addWidget(auswahl_hinweis)
        auswahl_layout.addWidget(btn_auswahl_kopieren)
        auswahl_layout.addWidget(btn_auswahl_verschieben)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(self._btn_export)
        layout.addStretch(1)
        layout.addWidget(auswahl_gruppe)

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

    def _auswahl_exportieren(self, entfernen: bool) -> None:
        ausgewaehlte_als_pdf_exportieren(
            self, self.liste, entfernen=entfernen,
            dialog_titel=self.tr("PDF speichern unter"),
            dateiname_vorschlag=self.tr("auszug.pdf"),
            dialog_filter=self.tr("PDF-Datei (*.pdf)"),
            fortschritt_text=self.tr("PDF wird erstellt …"),
            fehler_titel=self.tr("Export fehlgeschlagen"),
            erfolg_titel=self.tr("Fertig"),
            erfolg_text_vorlage=self.tr("PDF gespeichert unter:\n{0}"),
            keine_auswahl_titel=self.tr("Keine Auswahl"),
            keine_auswahl_text=self.tr("Bitte zuerst Seiten in der Liste links auswählen."),
        )
