"""
DE: Werkzeug "Seiten teilen": Seiten in ein Raster aus Zeilen und Spalten
    zerschneiden -- eine Achse fuer einen einfachen Streifen, beide Achsen
    zusammen fuer ein echtes Raster (z. B. eine Anleitung mit mehreren
    Seiten pro gescanntem Blatt). Die Schnittlinien lassen sich per Maus
    verschieben, per Knopf gleichmaessig verteilen oder automatisch auf die
    ruhigste Bildstelle in der Naehe ausrichten (z. B. eine Heftmitte).
    Wie beim Dreh-Werkzeug laesst sich jede Aktion auf die aktuelle Seite,
    eine Auswahl oder alle Seiten anwenden.

EN: "Split pages" tool: cut pages into a grid of rows and columns -- one
    axis for a simple strip, both axes together for a true grid (e.g. a
    manual with several pages per scanned sheet). Cut lines can be dragged
    with the mouse, distributed evenly via a button, or automatically
    aligned to the quietest nearby image area (e.g. a booklet's gutter). As
    in the rotate tool, every action can be applied to the current page, a
    selection, or all pages.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.combine import export_pdf
from pdfkrams.core.document import SplitSpec, WorkingPage
from pdfkrams.core.export_dateien import export_einzeldateien, materialisiere_teilung
from pdfkrams.core.split import automatische_positionen, gleichmaessige_positionen
from pdfkrams.core.rotate import rotiertes_bild
from pdfkrams.gui.widgets.export_dialog import einzelexport_abfragen
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget, vorschau_pixmap
from pdfkrams.gui.widgets.split_canvas import SplitCanvas

_VORSCHAU_GROESSE = 1000

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"


def _pixmap_zu_pil(wp: WorkingPage):
    """DE: Die Seite so rendern, wie sie nach Drehung/Spiegelung tatsaechlich
    aussieht (fuer die Auto-Ausrichtung, die den Bildinhalt analysiert).
    EN: Render the page as it actually looks after rotation/mirroring (for
    auto-alignment, which analyzes the image content)."""
    bild, _dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
    return bild


class SplitToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zerschneiden von Seiten in ein Zeilen/Spalten-Raster.
        Arbeitet auf der von aussen uebergebenen, gemeinsamen Seitenliste.
    EN: GUI page for cutting pages into a row/column grid. Works on the
        shared page list passed in from outside.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste
        self._synchronisiere = False

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())

        # -- Vorschau + Aktionen / preview + actions --------------------
        self._canvas = SplitCanvas()
        self._canvas.linienGeaendert.connect(self._linien_von_canvas)
        self._canvas.zoomGeaendert.connect(self._zoom_anzeige_aktualisieren)
        self._canvas.ziehenBegonnen.connect(self.liste.vor_aenderung_sichern)

        hinweis = QLabel(
            self.tr("Gelbe Linien mit der Maus verschieben (Mauszeiger ändert sich über "
                   "einer Linie). Zum genauen Treffen bei eng stehenden Linien: mit "
                   "Strg/Cmd+Scrollen bzw. Pinch-Geste vergrößern (unter dem "
                   "Mauszeiger verankert), mit normalem Scrollen/Wischen verschieben. "
                   "Spalten und/oder Zeilen unten festlegen -- beide zusammen ergeben "
                   "ein Raster, z. B. für mehrere Seiten auf einem gescannten Blatt. "
                   "Die Teilung ist zunächst nur eingestellt -- erst „Teilung jetzt "
                   "anwenden“ zerschneidet wirklich und ersetzt die Seite in der Liste "
                   "durch ihre Teile, die sich dann eigenständig weiterbearbeiten "
                   "lassen (z. B. ein zweites Mal teilen).")
        )
        hinweis.setWordWrap(True)

        zoom_zeile = QHBoxLayout()
        btn_zoom_aus = QPushButton("−")
        btn_zoom_aus.setFixedWidth(32)
        btn_zoom_aus.setToolTip(self.tr("Verkleinern"))
        btn_zoom_aus.clicked.connect(lambda: self._canvas.zoom_schritt(1 / 1.4))
        self._zoom_label = QLabel(self.tr("100 %"))
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setFixedWidth(56)
        btn_zoom_ein = QPushButton("+")
        btn_zoom_ein.setFixedWidth(32)
        btn_zoom_ein.setToolTip(self.tr("Vergrößern"))
        btn_zoom_ein.clicked.connect(lambda: self._canvas.zoom_schritt(1.4))
        btn_einpassen = QPushButton(self.tr("Einpassen"))
        btn_einpassen.clicked.connect(self._canvas.einpassen)
        zoom_zeile.addWidget(btn_zoom_aus)
        zoom_zeile.addWidget(self._zoom_label)
        zoom_zeile.addWidget(btn_zoom_ein)
        zoom_zeile.addWidget(btn_einpassen)
        zoom_zeile.addStretch(1)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)

        gruppe = QGroupBox(self.tr("Teilung – anwenden auf:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        einstellungen_zeile = QHBoxLayout()
        self._spalten_feld = QSpinBox()
        self._spalten_feld.setRange(1, 20)
        self._spalten_feld.setValue(2)
        self._spalten_feld.setPrefix(self.tr("Spalten: "))
        self._spalten_feld.setToolTip(self.tr("Anzahl Teile senkrecht nebeneinander. 1 = keine senkrechten Schnitte."))
        self._zeilen_feld = QSpinBox()
        self._zeilen_feld.setRange(1, 20)
        self._zeilen_feld.setValue(1)
        self._zeilen_feld.setPrefix(self.tr("Zeilen: "))
        self._zeilen_feld.setToolTip(self.tr("Anzahl Teile waagerecht übereinander. 1 = keine waagerechten Schnitte."))
        einstellungen_zeile.addWidget(self._spalten_feld)
        einstellungen_zeile.addWidget(self._zeilen_feld)
        gruppe_layout.addLayout(einstellungen_zeile)

        aktionen_zeile = QHBoxLayout()
        btn_uebernehmen = QPushButton(self.tr("Übernehmen"))
        btn_uebernehmen.setToolTip(self.tr("Spalten/Zeilen auf den gewählten Bereich anwenden, gleichmäßig verteilt."))
        btn_uebernehmen.clicked.connect(self._uebernehmen)
        btn_gleichmaessig = QPushButton(self.tr("Gleichmäßig verteilen"))
        btn_gleichmaessig.clicked.connect(self._gleichmaessig_verteilen)
        btn_automatisch = QPushButton(self.tr("Automatisch ausrichten"))
        btn_automatisch.setToolTip(
            self.tr("Schnitte je Seite einzeln auf die ruhigste Bildstelle in der Nähe ziehen "
                   "(z. B. eine Heftmitte statt mitten im Text).")
        )
        btn_automatisch.clicked.connect(self._automatisch_ausrichten)
        aktionen_zeile.addWidget(btn_uebernehmen)
        aktionen_zeile.addWidget(btn_gleichmaessig)
        aktionen_zeile.addWidget(btn_automatisch)
        gruppe_layout.addLayout(aktionen_zeile)

        btn_entfernen_teilung = QPushButton(self.tr("Teilung entfernen"))
        btn_entfernen_teilung.clicked.connect(self._teilung_entfernen)
        gruppe_layout.addWidget(btn_entfernen_teilung)

        self._btn_anwenden = QPushButton(self.tr("Teilung jetzt anwenden"))
        self._btn_anwenden.setToolTip(
            self.tr("Schneidet die Seiten im gewählten Bereich sofort auseinander. Die "
                   "Teile ersetzen die Originalseite als eigene, weiter bearbeitbare "
                   "Einträge in der Dateiliste -- z. B. um sie danach einzeln erneut zu "
                   "teilen, ohne vorher exportieren zu müssen.")
        )
        self._btn_anwenden.clicked.connect(self._teilung_anwenden)
        gruppe_layout.addWidget(self._btn_anwenden)

        self._btn_export = QPushButton(self.tr("Als eine PDF exportieren …"))
        self._btn_export.clicked.connect(self._exportieren)

        self._btn_export_einzeln = QPushButton(self.tr("Als einzelne nummerierte Dateien exportieren …"))
        self._btn_export_einzeln.setToolTip(
            self.tr("Jeder Teil wird eine eigene, durchnummerierte Datei in einem Zielordner "
                   "(z. B. 0001.pdf, 0002.pdf, …).")
        )
        self._btn_export_einzeln.clicked.connect(self._als_einzeldateien_exportieren)

        self.liste.geaendert.connect(self._export_aktivierung_aktualisieren)

        aussen = QVBoxLayout(self)
        aussen.addWidget(hinweis)
        aussen.addLayout(zoom_zeile)
        aussen.addWidget(self._canvas, 1)
        aussen.addWidget(gruppe)
        aussen.addStretch(0)
        aussen.addWidget(self._btn_export)
        aussen.addWidget(self._btn_export_einzeln)

        self._export_aktivierung_aktualisieren()
        self._auswahl_geaendert()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        # DE: Vorschau auch beim Werkzeugwechsel aktualisieren, nicht nur
        #     bei geaenderter Auswahl -- siehe rotate_tool.py fuer die
        #     ausfuehrliche Begruendung (gleiches Muster ueberall).
        # EN: Also refresh the preview when switching tools, not just on
        #     selection change -- see rotate_tool.py for the full
        #     rationale (same pattern everywhere).
        super().showEvent(event)
        self._auswahl_geaendert()

    # -- Geltungsbereich / scope resolution --------------------------------

    def _ziel_elemente(self) -> list[QListWidgetItem]:
        modus = self._geltungsbereich.currentData()
        if modus == _ALLE_SEITEN:
            return [self.liste.item(i) for i in range(self.liste.count())]
        if modus == _AUSGEWAEHLTE_SEITEN:
            gewaehlt = self.liste.selectedItems()
            if gewaehlt:
                return gewaehlt
        aktuell = self.liste.currentItem()
        return [aktuell] if aktuell else []

    # -- Auswahl / Vorschau laden --------------------------------------

    def _auswahl_geaendert(self) -> None:
        wp = self.liste.aktuelle_seite()
        if wp is None:
            self._canvas.seite_setzen(None, [], [])
            return
        pixmap = vorschau_pixmap(wp, _VORSCHAU_GROESSE)
        pos_v = wp.split.positionen_v if wp.split else []
        pos_h = wp.split.positionen_h if wp.split else []

        self._synchronisiere = True
        self._canvas.seite_setzen(pixmap, pos_v, pos_h)
        self._spalten_feld.setValue(len(pos_v) + 1)
        self._zeilen_feld.setValue(len(pos_h) + 1)
        self._synchronisiere = False

    def _zoom_anzeige_aktualisieren(self, zoom: float) -> None:
        self._zoom_label.setText(self.tr("{0} %").format(round(zoom * 100)))

    # -- Live-Verschieben der Linien / live line dragging -------------------

    def _linien_von_canvas(self, positionen_v: list[float], positionen_h: list[float]) -> None:
        if self._synchronisiere:
            return
        item = self.liste.currentItem()
        if item is None:
            return
        wp = item.data(Qt.ItemDataRole.UserRole)
        wp.split = SplitSpec(positionen_v=positionen_v, positionen_h=positionen_h)
        self.liste.item_aktualisieren(item)

    # -- Aktionen / actions --------------------------------------------

    def _uebernehmen(self) -> None:
        spalten = self._spalten_feld.value()
        zeilen = self._zeilen_feld.value()
        pos_v = gleichmaessige_positionen(spalten) if spalten > 1 else []
        pos_h = gleichmaessige_positionen(zeilen) if zeilen > 1 else []
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            wp.split = SplitSpec(positionen_v=pos_v, positionen_h=pos_h)
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _gleichmaessig_verteilen(self) -> None:
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            if wp.split is None:
                continue
            neue_v = gleichmaessige_positionen(len(wp.split.positionen_v) + 1) if wp.split.positionen_v else []
            neue_h = gleichmaessige_positionen(len(wp.split.positionen_h) + 1) if wp.split.positionen_h else []
            wp.split = SplitSpec(positionen_v=neue_v, positionen_h=neue_h)
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _automatisch_ausrichten(self) -> None:
        elemente = [item for item in self._ziel_elemente()
                   if item.data(Qt.ItemDataRole.UserRole).split is not None]
        if not elemente:
            QMessageBox.information(
                self, self.tr("Keine Teilung"),
                self.tr("Zuerst über „Übernehmen“ eine Teilung für den gewählten Bereich anlegen."),
            )
            return
        self.liste.vor_aenderung_sichern()
        anzeige = Fortschrittsanzeige(self, self.tr("Schnitte werden ausgerichtet …"), len(elemente))
        try:
            for i, item in enumerate(elemente, start=1):
                wp = item.data(Qt.ItemDataRole.UserRole)
                bild = _pixmap_zu_pil(wp)
                neue_v = (automatische_positionen(bild, "vertikal", len(wp.split.positionen_v) + 1)
                         if wp.split.positionen_v else [])
                neue_h = (automatische_positionen(bild, "waagerecht", len(wp.split.positionen_h) + 1)
                         if wp.split.positionen_h else [])
                wp.split = SplitSpec(positionen_v=neue_v, positionen_h=neue_h)
                self.liste.item_aktualisieren(item)
                anzeige.callback(i, len(elemente))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()
        self._auswahl_geaendert()

    def _teilung_entfernen(self) -> None:
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            wp.split = None
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _teilung_anwenden(self) -> None:
        """DE: Konfigurierte Teilungen im gewählten Bereich sofort ausführen
        und die Originaleinträge durch ihre Teile ersetzen.
        EN: Immediately carry out configured splits within the chosen scope
        and replace the original entries with their parts."""
        ziel = [item for item in self._ziel_elemente()
               if item.data(Qt.ItemDataRole.UserRole).split is not None]
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Teilung"),
                self.tr("Zuerst über „Übernehmen“ eine Teilung für den gewählten Bereich anlegen."),
            )
            return
        # DE: Von hinten nach vorn ersetzen, damit sich die Zeilennummern der
        #     noch nicht bearbeiteten Eintraege dabei nicht verschieben.
        #     stapelverarbeitung() buendelt alle Ersetzungen zu einem
        #     einzigen Rueckgaengig-Schritt.
        # EN: Replace back to front so the row numbers of not-yet-processed
        #     entries don't shift while doing so. stapelverarbeitung()
        #     bundles all replacements into a single undo step.
        anzeige = Fortschrittsanzeige(self, self.tr("Seiten werden geteilt …"), len(ziel))
        try:
            with self.liste.stapelverarbeitung():
                for i, item in enumerate(sorted(ziel, key=self.liste.row, reverse=True), start=1):
                    wp = item.data(Qt.ItemDataRole.UserRole)
                    neue_quellen = materialisiere_teilung(wp)
                    self.liste.ersetzen(item, neue_quellen)
                    anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()
        self._auswahl_geaendert()

    # -- Export -------------------------------------------------------------

    def _export_aktivierung_aktualisieren(self) -> None:
        an = self.liste.count() > 0
        self._btn_export.setEnabled(an)
        self._btn_export_einzeln.setEnabled(an)

    def _exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, self.tr("PDF speichern unter"), self.tr("geteilt.pdf"), self.tr("PDF-Datei (*.pdf)")
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

    def _als_einzeldateien_exportieren(self) -> None:
        einstellungen = einzelexport_abfragen(self)
        if einstellungen is None:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, self.tr("Dateien werden geschrieben …"), len(seiten))
        try:
            pfade = export_einzeldateien(
                seiten, einstellungen.zielordner, einstellungen.endung,
                basis=einstellungen.basis, start=einstellungen.start, stellen=einstellungen.stellen,
                fortschritt=anzeige.callback,
            )
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Export fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(
            self, self.tr("Fertig"), self.tr("{0} Dateien gespeichert in:\n{1}").format(len(pfade), einstellungen.zielordner)
        )
