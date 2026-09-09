"""
DE: Werkzeug "Seiten nummerieren": fuer eine durcheinandergeratene
    Seitenfolge -- jede Seite durchgehen und eintragen, an welcher Stelle
    sie im fertigen Dokument stehen soll, dann die Liste automatisch danach
    neu anordnen lassen. Es wird nichts auf die Seite geschrieben; ein
    bereits auf der Originalseite gedrucktes Seitenzahl bleibt unangetastet
    -- nur die Reihenfolge in der gemeinsamen Dateiliste aendert sich.

EN: "Number pages" tool: for a scrambled page sequence -- go through each
    page and note where it should end up in the finished document, then
    let the list automatically rearrange itself accordingly. Nothing is
    written onto the page; a page number already printed on the original
    page stays untouched -- only the order in the shared file list changes.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.combine import export_pdf
from pdfkrams.core.datumssortierung import natuerlich, seiten_zeitstempel
from pdfkrams.core.document import WorkingPage
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget, vorschau_pixmap
from pdfkrams.gui.widgets.umbenennen_dialog import umbenennen_dialog_oeffnen

_VORSCHAU_GROESSE = 900


class NummerierenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zuweisen von Zielnummern und das Neuanordnen der Liste.
    EN: GUI page for assigning target numbers and rearranging the list.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())

        hinweis = QLabel(
            self.tr("Für eine durcheinandergeratene Seitenfolge: jede Seite links "
                   "auswählen und hier eintragen, an welcher Stelle sie im "
                   "fertigen Dokument stehen soll. Es wird nichts auf die Seite "
                   "geschrieben -- ein „Zuweisen & weiter“ merkt sich nur die "
                   "Zielnummer und springt automatisch zur nächsten Seite. Am "
                   "Ende „Jetzt neu anordnen“ klicken, damit die Dateiliste "
                   "entsprechend sortiert wird.")
        )
        hinweis.setWordWrap(True)

        self._vorschau = QLabel(self.tr("Keine Seite ausgewählt"))
        self._vorschau.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vorschau.setStyleSheet("background: #2b2b2b; color: #aaaaaa;")
        self._vorschau.setMinimumHeight(300)
        self._vorschau.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        zeile = QHBoxLayout()
        self._nummer_feld = QSpinBox()
        self._nummer_feld.setRange(1, 999999)
        self._nummer_feld.setValue(1)
        self._nummer_feld.setPrefix(self.tr("Zielnummer: "))
        btn_zuweisen = QPushButton(self.tr("Zuweisen && weiter"))
        btn_zuweisen.clicked.connect(self._zuweisen)
        btn_entfernen = QPushButton(self.tr("Zuweisung entfernen"))
        btn_entfernen.clicked.connect(self._entfernen)
        zeile.addWidget(self._nummer_feld)
        zeile.addWidget(btn_zuweisen)
        zeile.addWidget(btn_entfernen)

        self._btn_anordnen = QPushButton(self.tr("Jetzt neu anordnen"))
        self._btn_anordnen.setToolTip(
            self.tr("Sortiert die gesamte Dateiliste nach den zugewiesenen "
                   "Zielnummern. Seiten ohne Zuweisung bleiben untereinander in "
                   "ihrer bisherigen Reihenfolge und landen am Ende.")
        )
        self._btn_anordnen.clicked.connect(self._neu_anordnen)

        manuell_gruppe = QGroupBox(self.tr("Von Hand (bei durcheinandergeratener Reihenfolge)"))
        manuell_layout = QVBoxLayout(manuell_gruppe)
        manuell_layout.addLayout(zeile)
        manuell_layout.addWidget(self._btn_anordnen)

        btn_datum_sortieren = QPushButton(self.tr("Automatisch nach Aufnahme-/Erstellungsdatum sortieren"))
        btn_datum_sortieren.setToolTip(
            self.tr("Sortiert die gesamte Dateiliste automatisch nach dem "
                   "verlässlichsten verfügbaren Zeitstempel jeder Seite: zuerst "
                   "die Aufnahmezeit im Bild selbst, sonst das PDF-Erstellungsdatum, "
                   "sonst die Erstellungszeit der Datei.")
        )
        btn_datum_sortieren.clicked.connect(self._nach_datum_sortieren)

        btn_dateien_umbenennen = QPushButton(self.tr("Dateien auf der Platte nach Datum umbenennen …"))
        btn_dateien_umbenennen.setToolTip(
            self.tr("Unabhängig von der Dateiliste hier: benennt Dateien in einem "
                   "Ordner durchlaufend um, sortiert nach Aufnahme-/"
                   "Erstellungsdatum oder nach Namen -- wie das frühere "
                   "benennen.py-Skript.")
        )
        btn_dateien_umbenennen.clicked.connect(self._dateien_umbenennen)

        automatisch_gruppe = QGroupBox(self.tr("Automatisch nach Datum"))
        automatisch_layout = QVBoxLayout(automatisch_gruppe)
        automatisch_layout.addWidget(btn_datum_sortieren)
        automatisch_layout.addWidget(btn_dateien_umbenennen)

        self._btn_export = QPushButton(self.tr("Als PDF exportieren …"))
        self._btn_export.clicked.connect(self._exportieren)
        self._btn_export.setEnabled(self.liste.count() > 0)
        self.liste.geaendert.connect(
            lambda: self._btn_export.setEnabled(self.liste.count() > 0)
        )

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(self._vorschau, 1)
        layout.addWidget(manuell_gruppe)
        layout.addWidget(automatisch_gruppe)
        layout.addWidget(self._btn_export)

        self._auswahl_geaendert()

    def _auswahl_geaendert(self) -> None:
        wp = self.liste.aktuelle_seite()
        if wp is None:
            self._vorschau.clear()
            self._vorschau.setText(self.tr("Keine Seite ausgewählt"))
            return
        pixmap = vorschau_pixmap(wp, _VORSCHAU_GROESSE)
        self._vorschau.setPixmap(
            pixmap.scaled(
                self._vorschau.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        if wp.ziel_nummer is not None:
            self._nummer_feld.setValue(wp.ziel_nummer)

    def _zuweisen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        self.liste.vor_aenderung_sichern()
        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        wp.ziel_nummer = self._nummer_feld.value()
        self.liste.item_aktualisieren(item)

        self._nummer_feld.setValue(self._nummer_feld.value() + 1)
        naechste_zeile = self.liste.row(item) + 1
        if naechste_zeile < self.liste.count():
            self.liste.setCurrentRow(naechste_zeile)

    def _entfernen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        self.liste.vor_aenderung_sichern()
        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        wp.ziel_nummer = None
        self.liste.item_aktualisieren(item)

    def _neu_anordnen(self) -> None:
        anzahl = self.liste.count()
        if anzahl == 0:
            return
        items = [self.liste.item(i) for i in range(anzahl)]
        zugewiesen = sum(1 for it in items if it.data(Qt.ItemDataRole.UserRole).ziel_nummer is not None)

        def schluessel(item):
            wp = item.data(Qt.ItemDataRole.UserRole)
            return (0, wp.ziel_nummer) if wp.ziel_nummer is not None else (1, 0)

        neue_reihenfolge = sorted(items, key=schluessel)
        self.liste.neu_anordnen(neue_reihenfolge)

        hinweis = self.tr("{0} von {1} Seiten hatten eine Zielnummer.").format(zugewiesen, anzahl)
        if zugewiesen < anzahl:
            hinweis += " " + self.tr("Die übrigen bleiben in ihrer bisherigen Reihenfolge am Ende.")
        QMessageBox.information(self, self.tr("Neu angeordnet"), hinweis)

    def _nach_datum_sortieren(self) -> None:
        anzahl = self.liste.count()
        if anzahl == 0:
            return
        items = [self.liste.item(i) for i in range(anzahl)]
        bewertet = []
        for item in items:
            wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
            zeit, quelle = seiten_zeitstempel(wp.source)
            bewertet.append((item, zeit, quelle))

        bewertet.sort(key=lambda t: (
            t[1], natuerlich(t[0].data(Qt.ItemDataRole.UserRole).source.path.name),
            t[0].data(Qt.ItemDataRole.UserRole).source.index,
        ))
        neue_reihenfolge = [item for item, _, _ in bewertet]
        self.liste.neu_anordnen(neue_reihenfolge)

        quellen_verwendet = sorted({quelle for _, _, quelle in bewertet})
        QMessageBox.information(
            self, self.tr("Sortiert"),
            self.tr("{0} Seiten nach Datum sortiert. Verwendete Zeitquelle(n): {1}.").format(
                anzahl, ", ".join(quellen_verwendet)
            ),
        )

    def _dateien_umbenennen(self) -> None:
        umbenennen_dialog_oeffnen(self)

    def _exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, self.tr("PDF speichern unter"), self.tr("sortiert.pdf"), self.tr("PDF-Datei (*.pdf)")
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
