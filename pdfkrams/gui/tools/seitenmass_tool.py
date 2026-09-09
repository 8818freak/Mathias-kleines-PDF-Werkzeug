"""
DE: Werkzeug "Seitenmaß normieren": Seiten auf eine exakte physische
    Zielgröße bringen -- ein DIN-A-Format oder ein freies Maß in mm.
    Schwarze Scan-Ränder (z. B. wenn die Vorlage kleiner als das
    Scannerglas war) werden dabei automatisch erkannt und abgeschnitten;
    ohne erkennbaren Rand wird die Seite direkt skaliert. Wie bei den
    anderen Werkzeugen wahlweise auf die aktuelle Seite, eine Auswahl
    oder alle Seiten anwendbar -- für ein Dokument mit mehreren
    Abschnitten unterschiedlicher Zielgröße das Werkzeug entsprechend
    mehrfach mit jeweils passender Auswahl anwenden.

EN: "Normalize page size" tool: bring pages to an exact physical target
    size -- a DIN A format or a free size in mm. Black scan borders
    (e.g. when the original was smaller than the scanner bed) are
    automatically detected and cropped away; without a detectable
    border, the page is scaled directly. Like the other tools, applicable
    to the current page, a selection, or all pages -- for a document with
    several sections needing different target sizes, run the tool
    several times with the matching selection each time.
"""

from __future__ import annotations

import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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

from pdfkrams.core import arbeitsordner
from pdfkrams.core.export_dateien import bild_materialisieren
from pdfkrams.core.rotate import rotiertes_bild
from pdfkrams.core.seitenmass import (
    DIN_GROESSEN,
    aktuelle_groesse_mm,
    naheliegende_din_groesse,
    schwarzen_rand_erkennen,
    seite_normieren,
)
from pdfkrams.gui.widgets.page_list import PageListWidget

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"

_BENUTZERDEFINIERT = "Benutzerdefiniert …"

# DE: Hoechstens so viele Zeilen in der Maß-Übersicht anzeigen, der Rest
#     wird zusammengefasst -- sonst wird die Liste bei "Alle Seiten" bei
#     vielseitigen Dokumenten unhandlich lang.
# EN: Show at most this many lines in the size overview, the rest gets
#     summarized -- otherwise the list becomes unwieldy for many-page
#     documents with "all pages".
_MAX_UEBERSICHT_ZEILEN = 12


class SeitenmassToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Normieren der Seitengroesse.
    EN: GUI page for normalizing page size.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        self._letzter_vorschlag: tuple[str | None, float, float] | None = None

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())

        hinweis = QLabel(
            "Bringt Seiten auf eine exakte physische Zielgröße -- ein DIN-"
            "A-Format oder ein freies Maß in mm. Schwarze Scan-Ränder "
            "(z. B. wenn die Vorlage kleiner als das Scannerglas war) "
            "werden dabei je Kante automatisch erkannt und abgeschnitten; "
            "ohne erkennbaren Rand wird direkt skaliert. Für ein Dokument "
            "mit mehreren Abschnitten unterschiedlicher Zielgröße: das "
            "Werkzeug mehrfach mit jeweils passender Auswahl anwenden."
        )
        hinweis.setWordWrap(True)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItems([_AKTUELLE_SEITE, _AUSGEWAEHLTE_SEITEN, _ALLE_SEITEN])
        self._geltungsbereich.currentTextChanged.connect(self._auswahl_geaendert)

        gruppe = QGroupBox("Zielgröße – anwenden auf:")
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        self._format_feld = QComboBox()
        self._format_feld.addItems(list(DIN_GROESSEN.keys()) + [_BENUTZERDEFINIERT])
        self._format_feld.setCurrentText("A4")
        self._format_feld.currentTextChanged.connect(self._format_geaendert)
        gruppe_layout.addWidget(self._format_feld)

        benutzerdefiniert_zeile = QHBoxLayout()
        self._breite_feld = QDoubleSpinBox()
        self._breite_feld.setRange(10.0, 5000.0)
        self._breite_feld.setValue(210.0)
        self._breite_feld.setPrefix("Breite: ")
        self._breite_feld.setSuffix(" mm")
        self._hoehe_feld = QDoubleSpinBox()
        self._hoehe_feld.setRange(10.0, 5000.0)
        self._hoehe_feld.setValue(297.0)
        self._hoehe_feld.setPrefix("Höhe: ")
        self._hoehe_feld.setSuffix(" mm")
        benutzerdefiniert_zeile.addWidget(self._breite_feld)
        benutzerdefiniert_zeile.addWidget(self._hoehe_feld)
        gruppe_layout.addLayout(benutzerdefiniert_zeile)
        self._breite_feld.setEnabled(False)
        self._hoehe_feld.setEnabled(False)

        self._dpi_feld = QSpinBox()
        self._dpi_feld.setRange(50, 1200)
        self._dpi_feld.setValue(300)
        self._dpi_feld.setPrefix("Ausgabeauflösung: ")
        self._dpi_feld.setSuffix(" dpi")
        gruppe_layout.addWidget(self._dpi_feld)

        self._rand_feld = QCheckBox("Schwarze Ränder automatisch abschneiden")
        self._rand_feld.setChecked(True)
        self._rand_feld.toggled.connect(self._auswahl_geaendert)
        gruppe_layout.addWidget(self._rand_feld)

        self._rand_info = QLabel()
        self._rand_info.setWordWrap(True)
        self._rand_info.setStyleSheet("color: gray;")
        gruppe_layout.addWidget(self._rand_info)

        self._vorschlag_info = QLabel()
        self._vorschlag_info.setWordWrap(True)
        gruppe_layout.addWidget(self._vorschlag_info)

        vorschlag_zeile = QHBoxLayout()
        vorschlag_zeile.addStretch(1)
        self._btn_vorschlag = QPushButton("Gemessene Größe übernehmen")
        self._btn_vorschlag.setToolTip(
            "Die gemessene Größe der aktuellen Seite als Zielgröße oben einsetzen."
        )
        self._btn_vorschlag.clicked.connect(self._vorschlag_uebernehmen)
        self._btn_vorschlag.setEnabled(False)
        vorschlag_zeile.addWidget(self._btn_vorschlag)
        gruppe_layout.addLayout(vorschlag_zeile)

        self._btn_anwenden = QPushButton("Anwenden")
        self._btn_anwenden.clicked.connect(self._anwenden)
        gruppe_layout.addWidget(self._btn_anwenden)

        uebersicht_gruppe = QGroupBox("Gemessene Größe je Seite im gewählten Bereich")
        uebersicht_layout = QVBoxLayout(uebersicht_gruppe)
        self._uebersicht_info = QLabel()
        self._uebersicht_info.setWordWrap(True)
        self._uebersicht_info.setStyleSheet("color: gray;")
        uebersicht_layout.addWidget(self._uebersicht_info)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(gruppe)
        layout.addWidget(uebersicht_gruppe)
        layout.addStretch(1)

        self._format_geaendert(self._format_feld.currentText())
        self._auswahl_geaendert()

    # -- Format-Auswahl / format selection ---------------------------------

    def _format_geaendert(self, text: str) -> None:
        benutzerdefiniert = text == _BENUTZERDEFINIERT
        self._breite_feld.setEnabled(benutzerdefiniert)
        self._hoehe_feld.setEnabled(benutzerdefiniert)
        if not benutzerdefiniert:
            self._breite_feld.setValue(DIN_GROESSEN[text][0])
            self._hoehe_feld.setValue(DIN_GROESSEN[text][1])

    # -- Geltungsbereich / scope resolution --------------------------------

    def _ziel_elemente(self) -> list[QListWidgetItem]:
        modus = self._geltungsbereich.currentText()
        if modus == _ALLE_SEITEN:
            return [self.liste.item(i) for i in range(self.liste.count())]
        if modus == _AUSGEWAEHLTE_SEITEN:
            gewaehlt = self.liste.selectedItems()
            if gewaehlt:
                return gewaehlt
        aktuell = self.liste.currentItem()
        return [aktuell] if aktuell else []

    # -- Randvorschau + Groessenuebersicht / border preview + size overview

    def _auswahl_geaendert(self) -> None:
        self._aktuelle_seite_info_aktualisieren()
        self._uebersicht_aktualisieren()

    def _aktuelle_seite_info_aktualisieren(self) -> None:
        wp = self.liste.aktuelle_seite()
        rand_abschneiden = self._rand_feld.isChecked()
        if wp is None:
            self._rand_info.setText("")
            self._vorschlag_info.setText("")
            self._btn_vorschlag.setEnabled(False)
            self._letzter_vorschlag = None
            return

        if rand_abschneiden:
            bild, _dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
            links, oben, rechts, unten = schwarzen_rand_erkennen(bild)
            if max(links, oben, rechts, unten) < 0.005:
                self._rand_info.setText("Kein schwarzer Rand an der aktuellen Seite erkannt.")
            else:
                self._rand_info.setText(
                    f"Erkannter Rand an der aktuellen Seite -- "
                    f"links {links*100:.1f} %, oben {oben*100:.1f} %, "
                    f"rechts {rechts*100:.1f} %, unten {unten*100:.1f} %."
                )
        else:
            self._rand_info.setText("")

        breite_mm, hoehe_mm = aktuelle_groesse_mm(wp, rand_abschneiden)
        vorschlag = naheliegende_din_groesse(breite_mm, hoehe_mm)
        self._letzter_vorschlag = (vorschlag, breite_mm, hoehe_mm)
        self._btn_vorschlag.setEnabled(True)
        if vorschlag:
            self._vorschlag_info.setText(
                f"Aktuelle Seite gemessen: {breite_mm:.1f} × {hoehe_mm:.1f} mm -- "
                f"entspricht ungefähr DIN {vorschlag} "
                f"({DIN_GROESSEN[vorschlag][0]:.0f} × {DIN_GROESSEN[vorschlag][1]:.0f} mm)."
            )
        else:
            self._vorschlag_info.setText(
                f"Aktuelle Seite gemessen: {breite_mm:.1f} × {hoehe_mm:.1f} mm -- "
                f"entspricht keinem DIN-A-Format."
            )

    def _uebersicht_aktualisieren(self) -> None:
        elemente = self._ziel_elemente()
        if not elemente:
            self._uebersicht_info.setText("Keine Seiten im gewählten Bereich.")
            return
        rand_abschneiden = self._rand_feld.isChecked()
        zeilen = []
        for item in elemente[:_MAX_UEBERSICHT_ZEILEN]:
            wp = item.data(Qt.ItemDataRole.UserRole)
            breite_mm, hoehe_mm = aktuelle_groesse_mm(wp, rand_abschneiden)
            vorschlag = naheliegende_din_groesse(breite_mm, hoehe_mm)
            zeile = f"{self.liste.row(item) + 1}. {breite_mm:.1f} × {hoehe_mm:.1f} mm"
            if vorschlag:
                zeile += f" (≈ DIN {vorschlag})"
            zeilen.append(zeile)
        if len(elemente) > _MAX_UEBERSICHT_ZEILEN:
            zeilen.append(f"… und {len(elemente) - _MAX_UEBERSICHT_ZEILEN} weitere Seite(n).")
        self._uebersicht_info.setText("\n".join(zeilen))

    def _vorschlag_uebernehmen(self) -> None:
        if self._letzter_vorschlag is None:
            return
        vorschlag, breite_mm, hoehe_mm = self._letzter_vorschlag
        if vorschlag:
            self._format_feld.setCurrentText(vorschlag)
        else:
            self._format_feld.setCurrentText(_BENUTZERDEFINIERT)
            self._breite_feld.setValue(breite_mm)
            self._hoehe_feld.setValue(hoehe_mm)

    # -- Anwenden / apply ----------------------------------------------------

    def _anwenden(self) -> None:
        ziel = self._ziel_elemente()
        if not ziel:
            QMessageBox.information(
                self, "Keine Auswahl", "Bitte zuerst Seiten in der Liste links auswählen."
            )
            return

        breite_mm = self._breite_feld.value()
        hoehe_mm = self._hoehe_feld.value()
        dpi = float(self._dpi_feld.value())
        rand_abschneiden = self._rand_feld.isChecked()
        arbeits_unterordner = arbeitsordner.pfad() / uuid.uuid4().hex

        with self.liste.stapelverarbeitung():
            for item in ziel:
                wp = item.data(Qt.ItemDataRole.UserRole)
                bild, ziel_dpi = seite_normieren(wp, breite_mm, hoehe_mm, dpi, rand_abschneiden)
                source = bild_materialisieren(bild, ziel_dpi, arbeits_unterordner, f"normiert_{uuid.uuid4().hex[:8]}")
                self.liste.ersetzen(item, [source])

        self._auswahl_geaendert()
        QMessageBox.information(
            self, "Fertig", f"{len(ziel)} Seite(n) auf {breite_mm:.0f} × {hoehe_mm:.0f} mm normiert."
        )
