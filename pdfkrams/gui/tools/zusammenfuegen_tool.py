"""
DE: Werkzeug "Seiten zusammenfügen": mehrere Seiten/Bilder zu einer
    einzigen, grossen Seite verbinden -- das Gegenstueck zum Teilen-
    Werkzeug. Gedacht fuer grossformatige Vorlagen (z. B. A1-Schaltplaene
    oder -Zeichnungen), die in mehreren kleineren Teilen (z. B. A4)
    gescannt wurden.

    Ausgewaehlte Seiten in der gewuenschten Reihenfolge auswaehlen, Anzahl
    Spalten festlegen und "Anordnung erzeugen" -- die Teile werden Kante
    an Kante in einem Raster platziert. Danach jede Kachel per Maus frei
    verschieben; fuer die ausgewaehlte Kachel laesst sich zusaetzlich eine
    Feindrehung und ein Beschnitt je Rand einstellen (Zahlenfelder statt
    Mausziehen -- praeziser fuer technische Zeichnungen, gleicht leicht
    unterschiedliche Scan-Raender bzw. bewusste Ueberlappung aus).
    "Übernehmen" ersetzt die urspruenglich ausgewaehlten Seiten in der
    Liste durch die eine zusammengefuegte Seite.

EN: "Combine pages" tool: merge several pages/images into a single large
    page -- the counterpart to the split tool. Meant for large-format
    originals (e.g. A1 schematics or drawings) that were scanned in
    several smaller parts (e.g. A4).

    Select the pages in the desired order, set the number of columns and
    click "Generate layout" -- the parts are placed edge-to-edge in a
    grid. Afterwards, freely drag each tile with the mouse; for the
    currently selected tile, a fine-alignment rotation and a per-edge
    crop can additionally be set (numeric fields instead of mouse
    dragging -- more precise for technical drawings, compensates for
    slightly different scan edges resp. deliberate overlap). "Apply"
    replaces the originally selected pages in the list with the one
    combined page.
"""

from __future__ import annotations

import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core import arbeitsordner
from pdfkrams.core.document import WorkingPage
from pdfkrams.core.export_dateien import bild_materialisieren
from pdfkrams.core.zusammenfuegen import Kachel, kachel_bild, raster_anordnen, zusammengefuegtes_bild
from pdfkrams.gui.bildkonvertierung import pil_zu_qpixmap
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.zusammenfuegen_canvas import ZusammenfuegenCanvas


def _kachel_eintrag(seite: WorkingPage, kachel: Kachel) -> tuple[int, float, float, float, float, object]:
    bild, dpi = kachel_bild(seite, kachel)
    breite_pt = bild.width / dpi * 72.0
    hoehe_pt = bild.height / dpi * 72.0
    return (kachel.index, kachel.x_pt, kachel.y_pt, breite_pt, hoehe_pt, pil_zu_qpixmap(bild))


class ZusammenfuegenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zusammenfuegen mehrerer Seiten zu einer.
    EN: GUI page for combining several pages into one.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste
        self._seiten: list[WorkingPage] = []
        self._items: list = []
        self._kacheln: list[Kachel] = []
        self._ausgewaehlter_index = -1

        hinweis = QLabel(
            self.tr("Für großformatige Vorlagen (z. B. Schaltpläne), die in mehreren "
                   "kleineren Teilen gescannt wurden: In der Dateiliste links die "
                   "Teile in der gewünschten Lesereihenfolge auswählen (Cmd/Shift-"
                   "Klick), Spaltenzahl festlegen und „Anordnung erzeugen“ -- die "
                   "Teile werden Kante an Kante in einem Raster platziert.\n\n"
                   "Danach jedes Teil mit der Maus frei verschieben (anklicken "
                   "wählt es aus). Für das ausgewählte Teil rechts eine "
                   "Feindrehung und einen Beschnitt je Rand einstellen, um leicht "
                   "unterschiedliche Scan-Ränder bzw. eine bewusste Überlappung "
                   "auszugleichen.")
        )
        hinweis.setWordWrap(True)

        einstellungen_zeile = QHBoxLayout()
        self._spalten_feld = QSpinBox()
        self._spalten_feld.setRange(1, 20)
        self._spalten_feld.setValue(2)
        self._spalten_feld.setPrefix(self.tr("Spalten: "))
        btn_anordnung = QPushButton(self.tr("Anordnung aus Auswahl erzeugen"))
        btn_anordnung.clicked.connect(self._anordnung_erzeugen)
        einstellungen_zeile.addWidget(self._spalten_feld)
        einstellungen_zeile.addWidget(btn_anordnung)

        self._canvas = ZusammenfuegenCanvas()
        self._canvas.kachelAusgewaehlt.connect(self._kachel_ausgewaehlt)
        self._canvas.kachelVerschoben.connect(self._kachel_verschoben)
        self._canvas.zoomGeaendert.connect(self._zoom_anzeige_aktualisieren)

        zoom_zeile = QHBoxLayout()
        btn_zoom_aus = QPushButton("−")
        btn_zoom_aus.setFixedWidth(32)
        btn_zoom_aus.clicked.connect(lambda: self._canvas.zoom_schritt(1 / 1.4))
        self._zoom_label = QLabel(self.tr("100 %"))
        self._zoom_label.setFixedWidth(56)
        btn_zoom_ein = QPushButton("+")
        btn_zoom_ein.setFixedWidth(32)
        btn_zoom_ein.clicked.connect(lambda: self._canvas.zoom_schritt(1.4))
        btn_einpassen = QPushButton(self.tr("Einpassen"))
        btn_einpassen.clicked.connect(self._canvas.einpassen)
        zoom_zeile.addWidget(btn_zoom_aus)
        zoom_zeile.addWidget(self._zoom_label)
        zoom_zeile.addWidget(btn_zoom_ein)
        zoom_zeile.addWidget(btn_einpassen)
        zoom_zeile.addStretch(1)

        # -- Feineinstellungen fuer die ausgewaehlte Kachel --------------
        self._feineinstellung_gruppe = QGroupBox(self.tr("Ausgewähltes Teil"))
        feineinstellung_layout = QVBoxLayout(self._feineinstellung_gruppe)

        self._rotation_feld = QDoubleSpinBox()
        self._rotation_feld.setRange(-180.0, 180.0)
        self._rotation_feld.setSingleStep(0.1)
        self._rotation_feld.setDecimals(1)
        self._rotation_feld.setPrefix(self.tr("Feindrehung: "))
        self._rotation_feld.setSuffix(" °")
        self._rotation_feld.valueChanged.connect(self._feineinstellung_geaendert)
        feineinstellung_layout.addWidget(self._rotation_feld)

        beschnitt_zeile1 = QHBoxLayout()
        self._beschnitt_links_feld = self._beschnitt_feld(self.tr("Links: "))
        self._beschnitt_rechts_feld = self._beschnitt_feld(self.tr("Rechts: "))
        beschnitt_zeile1.addWidget(self._beschnitt_links_feld)
        beschnitt_zeile1.addWidget(self._beschnitt_rechts_feld)
        beschnitt_zeile2 = QHBoxLayout()
        self._beschnitt_oben_feld = self._beschnitt_feld(self.tr("Oben: "))
        self._beschnitt_unten_feld = self._beschnitt_feld(self.tr("Unten: "))
        beschnitt_zeile2.addWidget(self._beschnitt_oben_feld)
        beschnitt_zeile2.addWidget(self._beschnitt_unten_feld)
        feineinstellung_layout.addWidget(QLabel(self.tr("Beschnitt je Rand:")))
        feineinstellung_layout.addLayout(beschnitt_zeile1)
        feineinstellung_layout.addLayout(beschnitt_zeile2)

        self._feineinstellung_gruppe.setEnabled(False)

        self._btn_uebernehmen = QPushButton(self.tr("Übernehmen"))
        self._btn_uebernehmen.setToolTip(
            self.tr("Setzt alle Teile gemäß ihrer aktuellen Anordnung zu einer Seite "
                   "zusammen und ersetzt die ursprünglich ausgewählten Seiten in der "
                   "Liste durch diese eine neue Seite.")
        )
        self._btn_uebernehmen.setEnabled(False)
        self._btn_uebernehmen.clicked.connect(self._uebernehmen)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addLayout(einstellungen_zeile)
        layout.addLayout(zoom_zeile)
        layout.addWidget(self._canvas, 1)
        layout.addWidget(self._feineinstellung_gruppe)
        layout.addWidget(self._btn_uebernehmen)

    def _beschnitt_feld(self, beschriftung: str) -> QDoubleSpinBox:
        feld = QDoubleSpinBox()
        feld.setRange(0.0, 45.0)
        feld.setSingleStep(0.5)
        feld.setDecimals(1)
        feld.setPrefix(beschriftung)
        feld.setSuffix(" %")
        feld.valueChanged.connect(self._feineinstellung_geaendert)
        return feld

    # -- Anordnung erzeugen / generate layout ------------------------------

    def _anordnung_erzeugen(self) -> None:
        items = sorted(self.liste.selectedItems(), key=self.liste.row)
        if len(items) < 2:
            QMessageBox.information(
                self, self.tr("Zu wenig ausgewählt"),
                self.tr("Bitte mindestens zwei Seiten in der Liste links auswählen "
                       "(in der gewünschten Reihenfolge)."),
            )
            return
        self._items = items
        self._seiten = [item.data(Qt.ItemDataRole.UserRole) for item in items]
        self._kacheln = raster_anordnen(self._seiten, self._spalten_feld.value())

        eintraege = [_kachel_eintrag(self._seiten[k.index], k) for k in self._kacheln]
        self._canvas.kacheln_setzen(eintraege)
        self._btn_uebernehmen.setEnabled(True)
        self._feineinstellung_gruppe.setEnabled(False)

    # -- Auswahl + Feineinstellung / selection + fine-tuning ---------------

    def _kachel_ausgewaehlt(self, index: int) -> None:
        self._ausgewaehlter_index = index
        self._feineinstellung_gruppe.setEnabled(index != -1)
        if index == -1:
            return
        kachel = self._kacheln[index]
        for feld, wert in (
            (self._rotation_feld, kachel.rotation),
            (self._beschnitt_links_feld, kachel.beschnitt_links * 100.0),
            (self._beschnitt_rechts_feld, kachel.beschnitt_rechts * 100.0),
            (self._beschnitt_oben_feld, kachel.beschnitt_oben * 100.0),
            (self._beschnitt_unten_feld, kachel.beschnitt_unten * 100.0),
        ):
            feld.blockSignals(True)
            feld.setValue(wert)
            feld.blockSignals(False)

    def _aktuelle_kachel(self) -> Kachel | None:
        index = self._ausgewaehlter_index
        if index == -1 or index >= len(self._kacheln):
            return None
        return self._kacheln[index]

    def _feineinstellung_geaendert(self, _wert: float) -> None:
        kachel = self._aktuelle_kachel()
        if kachel is None:
            return
        kachel.rotation = self._rotation_feld.value()
        kachel.beschnitt_links = self._beschnitt_links_feld.value() / 100.0
        kachel.beschnitt_rechts = self._beschnitt_rechts_feld.value() / 100.0
        kachel.beschnitt_oben = self._beschnitt_oben_feld.value() / 100.0
        kachel.beschnitt_unten = self._beschnitt_unten_feld.value() / 100.0
        _index, x_pt, y_pt, breite_pt, hoehe_pt, pixmap = _kachel_eintrag(self._seiten[kachel.index], kachel)
        self._canvas.kachel_aktualisieren(kachel.index, x_pt, y_pt, breite_pt, hoehe_pt, pixmap)

    def _kachel_verschoben(self, index: int, x_pt: float, y_pt: float) -> None:
        self._kacheln[index].x_pt = x_pt
        self._kacheln[index].y_pt = y_pt

    def _zoom_anzeige_aktualisieren(self, zoom: float) -> None:
        self._zoom_label.setText(self.tr("{0} %").format(round(zoom * 100)))

    # -- Übernehmen / apply -------------------------------------------------

    def _uebernehmen(self) -> None:
        anzeige = Fortschrittsanzeige(self, self.tr("Seite wird zusammengefügt …"), len(self._kacheln))
        try:
            bild, dpi = zusammengefuegtes_bild(self._seiten, self._kacheln, fortschritt=anzeige.callback)
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        ziel = arbeitsordner.pfad() / uuid.uuid4().hex
        source = bild_materialisieren(bild, dpi, ziel, "zusammengefuegt")
        self.liste.mehrere_ersetzen(self._items, [source])

        self._items = []
        self._seiten = []
        self._kacheln = []
        self._ausgewaehlter_index = -1
        self._canvas.kacheln_setzen([])
        self._btn_uebernehmen.setEnabled(False)
        self._feineinstellung_gruppe.setEnabled(False)

        QMessageBox.information(self, self.tr("Fertig"), self.tr("Die Teile wurden zu einer Seite zusammengefügt."))
