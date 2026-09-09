"""
DE: Werkzeug "Bildbereinigung": fuer gescannte Schwarzweiß-/Textvorlagen --
    Binarisieren (Schwellwert, auf Wunsch automatisch per Otsu-Verfahren
    vorgeschlagen) und Despeckle (kleine dunkle Flecken/Staub entfernen).
    Beide Schritte sind unabhaengig voneinander zuschaltbar. Wie bei den
    anderen Werkzeugen wahlweise auf die aktuelle Seite, eine Auswahl oder
    alle Seiten anwendbar. Binarisierte Seiten lassen sich anschliessend
    im Werkzeug "PDF verkleinern & PDF/A" oft deutlich kleiner komprimieren
    als das Original.

EN: "Image cleanup" tool: for scanned black-and-white/text originals --
    binarizing (threshold, optionally auto-suggested via Otsu's method)
    and despeckling (removing small dark specks/dust). Both steps can be
    toggled independently. Like the other tools, applicable to the
    current page, a selection, or all pages. Binarized pages can often be
    compressed significantly smaller than the original afterwards in the
    "Shrink PDF & PDF/A" tool.
"""

from __future__ import annotations

import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core import arbeitsordner
from pdfkrams.core.bildbereinigung import otsu_schwellwert, seite_bereinigen
from pdfkrams.core.export_dateien import bild_materialisieren
from pdfkrams.core.rotate import rotiertes_bild
from pdfkrams.gui.bildkonvertierung import pil_zu_qpixmap
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget

_VORSCHAU_GROESSE = 900

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"


class BildbereinigungToolWidget(QWidget):
    """
    DE: GUI-Seite fuer Binarisieren und Despeckle gescannter Seiten.
    EN: GUI page for binarizing and despeckling scanned pages.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())

        hinweis = QLabel(
            self.tr("Für gescannte Schwarzweiß-/Textvorlagen: wandelt in reines Schwarzweiß um "
                   "(Schwellwert, auf Wunsch automatisch vorgeschlagen) und/oder entfernt kleine "
                   "dunkle Flecken (Staub, Druckpunkte). Beide Schritte sind unabhängig "
                   "voneinander zuschaltbar; binarisierte Seiten lassen sich in „PDF "
                   "verkleinern & PDF/A“ oft besonders klein komprimieren.")
        )
        hinweis.setWordWrap(True)

        self._vorschau = QLabel(self.tr("Keine Seite ausgewählt"))
        self._vorschau.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vorschau.setStyleSheet("background: #2b2b2b; color: #aaaaaa;")
        self._vorschau.setMinimumHeight(300)
        self._vorschau.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)

        gruppe = QGroupBox(self.tr("Bereinigung – anwenden auf:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        schwellwert_zeile = QHBoxLayout()
        self._schwellwert_feld = QSpinBox()
        self._schwellwert_feld.setRange(0, 255)
        self._schwellwert_feld.setValue(128)
        self._schwellwert_feld.setPrefix(self.tr("Schwellwert: "))
        self._schwellwert_feld.valueChanged.connect(self._vorschau_aktualisieren)
        btn_otsu = QPushButton(self.tr("Automatisch vorschlagen"))
        btn_otsu.setToolTip(
            self.tr("Schlägt per Otsu-Verfahren einen Schwellwert vor, der Text/Linien am "
                   "deutlichsten vom Hintergrund trennt.")
        )
        btn_otsu.clicked.connect(self._schwellwert_vorschlagen)
        schwellwert_zeile.addWidget(self._schwellwert_feld)
        schwellwert_zeile.addWidget(btn_otsu)
        gruppe_layout.addLayout(schwellwert_zeile)

        self._binarisieren_feld = QCheckBox(self.tr("In reines Schwarzweiß umwandeln (Binarisieren)"))
        self._binarisieren_feld.setChecked(True)
        self._binarisieren_feld.toggled.connect(self._vorschau_aktualisieren)
        gruppe_layout.addWidget(self._binarisieren_feld)

        despeckle_zeile = QHBoxLayout()
        self._despeckle_feld = QSpinBox()
        self._despeckle_feld.setRange(0, 5)
        self._despeckle_feld.setValue(1)
        self._despeckle_feld.setPrefix(self.tr("Flecken entfernen (Stärke): "))
        self._despeckle_feld.setToolTip(
            self.tr("0 = aus. Je höher, desto größere Flecken verschwinden -- aber auch desto "
                   "eher leiden dünne Textstriche. 1-2 ist meist ein guter Start.")
        )
        self._despeckle_feld.valueChanged.connect(self._vorschau_aktualisieren)
        despeckle_zeile.addWidget(self._despeckle_feld)
        gruppe_layout.addLayout(despeckle_zeile)

        self._btn_anwenden = QPushButton(self.tr("Anwenden"))
        self._btn_anwenden.clicked.connect(self._anwenden)
        gruppe_layout.addWidget(self._btn_anwenden)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(self._vorschau, 1)
        layout.addWidget(gruppe)
        layout.addStretch(0)

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

    # -- Vorschau / preview -------------------------------------------------

    def _auswahl_geaendert(self) -> None:
        self._vorschau_aktualisieren()

    def _schwellwert_vorschlagen(self) -> None:
        wp = self.liste.aktuelle_seite()
        if wp is None:
            return
        bild, _dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
        self._schwellwert_feld.setValue(otsu_schwellwert(bild))

    def _vorschau_aktualisieren(self) -> None:
        wp = self.liste.aktuelle_seite()
        if wp is None:
            self._vorschau.clear()
            self._vorschau.setText(self.tr("Keine Seite ausgewählt"))
            return
        bild, _dpi = seite_bereinigen(
            wp, self._schwellwert_feld.value(), self._binarisieren_feld.isChecked(), self._despeckle_feld.value(),
        )
        pixmap = pil_zu_qpixmap(bild)
        self._vorschau.setPixmap(
            pixmap.scaled(
                max(self._vorschau.width(), _VORSCHAU_GROESSE), max(self._vorschau.height(), _VORSCHAU_GROESSE),
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
            )
        )

    # -- Anwenden / apply ----------------------------------------------------

    def _anwenden(self) -> None:
        ziel = self._ziel_elemente()
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Auswahl"), self.tr("Bitte zuerst Seiten in der Liste links auswählen.")
            )
            return

        schwellwert = self._schwellwert_feld.value()
        binarisieren = self._binarisieren_feld.isChecked()
        despeckle_staerke = self._despeckle_feld.value()
        arbeits_unterordner = arbeitsordner.pfad() / uuid.uuid4().hex

        anzeige = Fortschrittsanzeige(self, self.tr("Seiten werden bereinigt …"), len(ziel))
        try:
            with self.liste.stapelverarbeitung():
                for i, item in enumerate(ziel, start=1):
                    wp = item.data(Qt.ItemDataRole.UserRole)
                    bild, dpi = seite_bereinigen(wp, schwellwert, binarisieren, despeckle_staerke)
                    source = bild_materialisieren(bild, dpi, arbeits_unterordner, f"bereinigt_{uuid.uuid4().hex[:8]}")
                    self.liste.ersetzen(item, [source])
                    anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()

        self._auswahl_geaendert()
        QMessageBox.information(
            self, self.tr("Fertig"), self.tr("{0} Seite(n) bereinigt.").format(len(ziel))
        )
