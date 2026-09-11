"""
DE: Werkzeug "Seiten zuschneiden": Seiten von allen vier Raendern aus um
    ein frei waehlbares physisches Mass beschneiden -- z. B. um einen
    Lochrandstreifen, einen Heftrand oder ungewollten Rand-Inhalt
    praezise zu entfernen. Anders als "Seitenmaß normieren" wird dabei
    NICHT auf eine Zielgroesse skaliert, sondern genau das angegebene
    Mass abgeschnitten; die Ergebnisgroesse ergibt sich daraus und wird
    live in der eingestellten Maßeinheit angezeigt, inkl. Vorschlag des
    naheliegenden Papierformats. Wie bei den anderen Werkzeugen wahlweise
    auf die aktuelle Seite, eine Auswahl oder alle Seiten anwendbar -- die
    Randmasse bleiben dabei ueber einen Seitenwechsel hinweg erhalten,
    damit sich dasselbe feste Mass gezielt auf mehrere Seiten anwenden
    laesst ("im Block").

EN: "Crop pages" tool: trim pages from all four edges by a freely
    chosen physical amount -- e.g. to precisely remove a punch-hole
    strip, a binding margin, or unwanted content near an edge. Unlike
    "Normalize page size", this does NOT scale to a target size but cuts
    away exactly the specified amount; the resulting size follows from
    that and is shown live in the configured measurement unit, including
    a suggestion of the nearest paper format. Like the other tools,
    applicable to the current page, a selection, or all pages -- the
    margins persist across switching pages, so the same fixed amount can
    be applied to several pages on purpose ("in bulk").
"""

from __future__ import annotations

import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core import arbeitsordner
from pdfkrams.core.export_dateien import bild_materialisieren
from pdfkrams.core.seitenmass import aktuelle_groesse_mm, einheit_zu_mm, mm_zu_einheit, naheliegendes_format
from pdfkrams.core.zuschneiden import seite_zuschneiden
from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget, vorschau_pixmap
from pdfkrams.gui.widgets.zuschneiden_canvas import ZuschneidenCanvas

_VORSCHAU_GROESSE = 1000

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"


class ZuschneidenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zuschneiden von Seiten an allen vier Raendern.
    EN: GUI page for cropping pages on all four edges.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        # DE: Kanonische Randmasse in mm -- unabhaengig von der gerade
        #     angezeigten Masseinheit UND von der gerade ausgewaehlten
        #     Seite. Bleiben beim Wechsel der aktuellen Seite bewusst
        #     erhalten, damit sich dasselbe feste Mass auf mehrere Seiten
        #     anwenden laesst.
        # EN: Canonical margins in mm -- independent of the currently
        #     displayed measurement unit AND of the currently selected
        #     page. Deliberately preserved when the current page changes,
        #     so the same fixed amount can be applied to several pages.
        self._links_mm = 0.0
        self._oben_mm = 0.0
        self._rechts_mm = 0.0
        self._unten_mm = 0.0
        # DE: Volle physische Groesse der aktuell angezeigten Seite, ohne
        #     jeden Beschnitt -- Referenz fuer die Umrechnung mm <-> Anteil.
        # EN: Full physical size of the currently displayed page, without
        #     any cropping -- reference for converting mm <-> fraction.
        self._breite_mm = 210.0
        self._hoehe_mm = 297.0

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())
        einstellungen.masseinheitGeaendert.connect(self._masseinheit_aktualisieren)

        hinweis = QLabel(
            self.tr("Schneidet Seiten von allen vier Rändern aus um ein frei wählbares Maß "
                   "zu -- z. B. um einen Lochrandstreifen oder Heftrand präzise zu "
                   "entfernen. Anders als „Seitenmaß normieren“ wird dabei nicht auf eine "
                   "Zielgröße skaliert, sondern genau das angegebene Maß abgeschnitten. "
                   "Die Linien in der Vorschau lassen sich auch direkt mit der Maus "
                   "ziehen; der abgeschnittene Bereich wird abgedunkelt dargestellt.")
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
        btn_einpassen.clicked.connect(self._canvas_einpassen)
        zoom_zeile.addWidget(btn_zoom_aus)
        zoom_zeile.addWidget(self._zoom_label)
        zoom_zeile.addWidget(btn_zoom_ein)
        zoom_zeile.addWidget(btn_einpassen)
        zoom_zeile.addStretch(1)

        self._canvas = ZuschneidenCanvas()
        self._canvas.raenderGeaendert.connect(self._raender_von_canvas)
        self._canvas.zoomGeaendert.connect(self._zoom_anzeige_aktualisieren)
        self._canvas.ziehenBegonnen.connect(self.liste.vor_aenderung_sichern)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)

        gruppe = QGroupBox(self.tr("Zuschneiden – anwenden auf:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        raender_zeile1 = QHBoxLayout()
        self._links_feld = self._randfeld(self.tr("Links: "))
        self._rechts_feld = self._randfeld(self.tr("Rechts: "))
        raender_zeile1.addWidget(self._links_feld)
        raender_zeile1.addWidget(self._rechts_feld)
        raender_zeile2 = QHBoxLayout()
        self._oben_feld = self._randfeld(self.tr("Oben: "))
        self._unten_feld = self._randfeld(self.tr("Unten: "))
        raender_zeile2.addWidget(self._oben_feld)
        raender_zeile2.addWidget(self._unten_feld)
        gruppe_layout.addLayout(raender_zeile1)
        gruppe_layout.addLayout(raender_zeile2)
        self._masseinheit_feldformat_setzen(einstellungen.masseinheit())

        btn_zuruecksetzen = QPushButton(self.tr("Ränder zurücksetzen"))
        btn_zuruecksetzen.clicked.connect(self._raender_zuruecksetzen)
        gruppe_layout.addWidget(btn_zuruecksetzen)

        self._ergebnis_info = QLabel()
        self._ergebnis_info.setWordWrap(True)
        gruppe_layout.addWidget(self._ergebnis_info)

        self._btn_anwenden = QPushButton(self.tr("Anwenden"))
        self._btn_anwenden.clicked.connect(self._anwenden)
        gruppe_layout.addWidget(self._btn_anwenden)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addLayout(zoom_zeile)
        layout.addWidget(self._canvas, 1)
        layout.addWidget(gruppe)
        layout.addStretch(0)

        self._auswahl_geaendert()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        # DE: Vorschau auch beim Werkzeugwechsel aktualisieren, nicht nur
        #     bei geaenderter Auswahl -- siehe rotate_tool.py fuer die
        #     ausfuehrliche Begruendung (gleiches Muster ueberall). Genau
        #     das war der vom Nutzer gemeldete Fehler: nach Drehen+
        #     Speichern zeigte das Zuschneiden-Werkzeug weiter die alte,
        #     schiefe Seite, bis eine andere Seite ausgewaehlt wurde.
        # EN: Also refresh the preview when switching tools, not just on
        #     selection change -- see rotate_tool.py for the full
        #     rationale (same pattern everywhere). This was exactly the
        #     bug the user reported: after rotating+saving, the crop tool
        #     kept showing the old, skewed page until a different page
        #     was selected.
        super().showEvent(event)
        self._auswahl_geaendert()

    def _randfeld(self, beschriftung: str) -> QDoubleSpinBox:
        feld = QDoubleSpinBox()
        feld.setPrefix(beschriftung)
        feld.valueChanged.connect(self._benutzerdefiniert_geaendert)
        return feld

    # -- Masseinheit / measurement unit ------------------------------------

    def _masseinheit_feldformat_setzen(self, einheit: str) -> None:
        """DE: Nur Dezimalstellen/Schrittweite/Bereich/Suffix der Felder
            setzen -- ohne Werte zu aktualisieren (fuer __init__, bevor
            die Canvas ihren Zustand hat).
        EN: Only set the fields' decimals/step/range/suffix -- without
            refreshing values (for __init__, before the canvas has its
            state)."""
        if einheit == "in":
            dezimalstellen, schritt, maximum = 2, 0.05, 20.0
        else:
            dezimalstellen, schritt, maximum = 1, 0.5, 500.0
        for feld in (self._links_feld, self._oben_feld, self._rechts_feld, self._unten_feld):
            feld.blockSignals(True)
            feld.setDecimals(dezimalstellen)
            feld.setSingleStep(schritt)
            feld.setRange(0.0, maximum)
            feld.setSuffix(f" {einheit}")
            feld.blockSignals(False)

    def _masseinheit_aktualisieren(self, einheit: str) -> None:
        self._masseinheit_feldformat_setzen(einheit)
        self._felder_anzeigen()
        self._ergebnis_anzeigen()

    def _felder_anzeigen(self) -> None:
        """DE: Zahlenfelder aus den kanonischen mm-Werten in der aktuellen
        Masseinheit anzeigen, ohne Signale auszuloesen.
        EN: Display the number fields from the canonical mm values in the
        current measurement unit, without firing signals."""
        einheit = einstellungen.masseinheit()
        for feld, mm_wert in (
            (self._links_feld, self._links_mm), (self._oben_feld, self._oben_mm),
            (self._rechts_feld, self._rechts_mm), (self._unten_feld, self._unten_mm),
        ):
            feld.blockSignals(True)
            feld.setValue(mm_zu_einheit(mm_wert, einheit))
            feld.blockSignals(False)

    def _canvas_anzeigen(self) -> None:
        """DE: Canvas-Rand-Anteile aus den kanonischen mm-Werten und der
        aktuellen Seitengroesse berechnen und anzeigen.
        EN: Compute and display the canvas edge fractions from the
        canonical mm values and the current page size."""
        self._canvas.raender_setzen(
            self._links_mm / self._breite_mm if self._breite_mm else 0.0,
            self._oben_mm / self._hoehe_mm if self._hoehe_mm else 0.0,
            self._rechts_mm / self._breite_mm if self._breite_mm else 0.0,
            self._unten_mm / self._hoehe_mm if self._hoehe_mm else 0.0,
        )

    def _benutzerdefiniert_geaendert(self, _wert: float) -> None:
        einheit = einstellungen.masseinheit()
        self._links_mm = einheit_zu_mm(self._links_feld.value(), einheit)
        self._oben_mm = einheit_zu_mm(self._oben_feld.value(), einheit)
        self._rechts_mm = einheit_zu_mm(self._rechts_feld.value(), einheit)
        self._unten_mm = einheit_zu_mm(self._unten_feld.value(), einheit)
        self._canvas_anzeigen()
        self._ergebnis_anzeigen()

    def _raender_von_canvas(self, links: float, oben: float, rechts: float, unten: float) -> None:
        self._links_mm = links * self._breite_mm
        self._oben_mm = oben * self._hoehe_mm
        self._rechts_mm = rechts * self._breite_mm
        self._unten_mm = unten * self._hoehe_mm
        self._felder_anzeigen()
        self._ergebnis_anzeigen()

    def _raender_zuruecksetzen(self) -> None:
        self._links_mm = self._oben_mm = self._rechts_mm = self._unten_mm = 0.0
        self._felder_anzeigen()
        self._canvas_anzeigen()
        self._ergebnis_anzeigen()

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

    # -- Vorschau / preview -------------------------------------------------

    def _auswahl_geaendert(self) -> None:
        wp = self.liste.aktuelle_seite()
        if wp is None:
            self._canvas.seite_setzen(None, 0.0, 0.0, 0.0, 0.0)
            self._ergebnis_info.setText("")
            return
        self._breite_mm, self._hoehe_mm = aktuelle_groesse_mm(wp, rand_abschneiden=False)
        pixmap = vorschau_pixmap(wp, _VORSCHAU_GROESSE)
        self._canvas.seite_setzen(
            pixmap,
            self._links_mm / self._breite_mm if self._breite_mm else 0.0,
            self._oben_mm / self._hoehe_mm if self._hoehe_mm else 0.0,
            self._rechts_mm / self._breite_mm if self._breite_mm else 0.0,
            self._unten_mm / self._hoehe_mm if self._hoehe_mm else 0.0,
        )
        self._ergebnis_anzeigen()

    def _canvas_einpassen(self) -> None:
        self._canvas.einpassen()

    def _zoom_anzeige_aktualisieren(self, zoom: float) -> None:
        self._zoom_label.setText(self.tr("{0} %").format(round(zoom * 100)))

    def _ergebnis_anzeigen(self) -> None:
        einheit = einstellungen.masseinheit()
        dezimalstellen = 2 if einheit == "in" else 1
        ziel_breite_mm = max(0.0, self._breite_mm - self._links_mm - self._rechts_mm)
        ziel_hoehe_mm = max(0.0, self._hoehe_mm - self._oben_mm - self._unten_mm)
        b = mm_zu_einheit(ziel_breite_mm, einheit)
        h = mm_zu_einheit(ziel_hoehe_mm, einheit)
        text = self.tr("Ergebnisgröße der aktuellen Seite: {0} × {1} {2}").format(
            f"{b:.{dezimalstellen}f}", f"{h:.{dezimalstellen}f}", einheit
        )
        vorschlag = naheliegendes_format(ziel_breite_mm, ziel_hoehe_mm)
        if vorschlag:
            text += self.tr(" (≈ {0})").format(vorschlag)
        self._ergebnis_info.setText(text)

    # -- Anwenden / apply ----------------------------------------------------

    def _anwenden(self) -> None:
        ziel = self._ziel_elemente()
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Auswahl"), self.tr("Bitte zuerst Seiten in der Liste links auswählen.")
            )
            return

        links_mm, oben_mm = self._links_mm, self._oben_mm
        rechts_mm, unten_mm = self._rechts_mm, self._unten_mm
        arbeits_unterordner = arbeitsordner.pfad() / uuid.uuid4().hex

        anzeige = Fortschrittsanzeige(self, self.tr("Seiten werden zugeschnitten …"), len(ziel))
        try:
            with self.liste.stapelverarbeitung():
                for i, item in enumerate(ziel, start=1):
                    wp = item.data(Qt.ItemDataRole.UserRole)
                    bild, dpi = seite_zuschneiden(wp, links_mm, oben_mm, rechts_mm, unten_mm)
                    source = bild_materialisieren(bild, dpi, arbeits_unterordner, f"zugeschnitten_{uuid.uuid4().hex[:8]}")
                    self.liste.ersetzen(item, [source])
                    anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()

        self._auswahl_geaendert()
        QMessageBox.information(
            self, self.tr("Fertig"), self.tr("{0} Seite(n) zugeschnitten.").format(len(ziel))
        )
