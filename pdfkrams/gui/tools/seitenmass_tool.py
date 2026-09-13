"""
DE: Werkzeug "Seitenmaß normieren": Seiten auf eine exakte physische
    Zielgröße bringen -- ein DIN-A-Format oder ein freies Maß in mm.
    Schwarze Scan-Ränder (z. B. wenn die Vorlage kleiner als das
    Scannerglas war) werden dabei automatisch erkannt und abgeschnitten;
    ohne erkennbaren Rand wird die Seite direkt skaliert. Wie bei den
    anderen Werkzeugen wahlweise auf die aktuelle Seite, eine Auswahl
    oder alle Seiten anwendbar. Alternativ per Automatik-Modus: jede
    Seite wird einzeln vermessen und auf ihr eigenes naheliegendstes
    bekanntes Format normiert (z. B. A3-Deckblatt + A4-Innenseiten in
    einem Rutsch, ohne die Auswahl manuell zu unterteilen).

EN: "Normalize page size" tool: bring pages to an exact physical target
    size -- a DIN A format or a free size in mm. Black scan borders
    (e.g. when the original was smaller than the scanner bed) are
    automatically detected and cropped away; without a detectable
    border, the page is scaled directly. Like the other tools, applicable
    to the current page, a selection, or all pages. Alternatively, via
    automatic mode: each page is measured individually and normalized to
    its own nearest known format (e.g. an A3 cover plus A4 inner pages
    in one pass, without manually splitting up the selection).
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
    PAPIERFORMATE,
    aktuelle_groesse_mm,
    einheit_zu_mm,
    mm_zu_einheit,
    naechstes_format,
    naheliegendes_format,
    schwarzen_rand_erkennen,
    seite_automatisch_normieren,
    seite_normieren,
)
from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
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
        # DE: Waehrend _anwenden() laeuft True -- siehe _auswahl_geaendert()
        #     fuer die Begruendung, warum das die Zwischenaktualisierung
        #     der Uebersicht unterdrueckt.
        # EN: True while _anwenden() is running -- see
        #     _auswahl_geaendert() for why this suppresses the overview's
        #     intermediate refresh.
        self._stapel_laeuft = False
        # DE: Kanonischer Zielwert in mm -- unabhaengig von der gerade
        #     angezeigten Masseinheit. Die Zahlenfelder zeigen nur eine
        #     UMGERECHNETE Ansicht davon; das eigentliche Anwenden nutzt
        #     immer diese beiden Werte.
        # EN: Canonical target value in mm -- independent of whichever
        #     measurement unit is currently displayed. The spin boxes
        #     only show a CONVERTED view of this; actually applying
        #     always uses these two values.
        self._breite_mm = PAPIERFORMATE["A4"][0]
        self._hoehe_mm = PAPIERFORMATE["A4"][1]

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())
        einstellungen.masseinheitGeaendert.connect(self._masseinheit_aktualisieren)

        hinweis = QLabel(
            self.tr("Bringt Seiten auf eine exakte physische Zielgröße -- ein DIN-"
                   "A-Format, ein US-Format oder ein freies Maß. Hoch- und Querformat "
                   "werden dabei je Seite automatisch erkannt: eine quer liegende Seite "
                   "wird nicht gedreht, sondern bekommt automatisch die quere Variante "
                   "des Zielmaßes (z. B. A4 quer bleibt quer) -- eine Datei mit "
                   "gemischt hoch/quer eingescannten Seiten kann daher in einem Rutsch "
                   "normiert werden. Schwarze Scan-Ränder (z. B. wenn die Vorlage "
                   "kleiner als das Scannerglas war) werden dabei je Kante automatisch "
                   "erkannt und abgeschnitten; ohne erkennbaren Rand wird direkt "
                   "skaliert. Für ein Dokument mit mehreren Abschnitten "
                   "unterschiedlicher Zielgröße: entweder das Werkzeug mehrfach mit "
                   "jeweils passender Auswahl anwenden, oder unten den "
                   "Automatik-Modus aktivieren, der jede Seite einzeln vermisst und "
                   "auf ihr eigenes naheliegendstes Format normiert.")
        )
        hinweis.setWordWrap(True)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)
        self._geltungsbereich.currentIndexChanged.connect(self._auswahl_geaendert)

        gruppe = QGroupBox(self.tr("Zielgröße – anwenden auf:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        # DE: Formatnamen (A4, US Letter, …) selbst NICHT uebersetzen -- das
        #     sind stehende, sprachunabhaengige Bezeichnungen. Nur der
        #     "Benutzerdefiniert"-Eintrag braucht eine Uebersetzung, daher
        #     ueber addItem(Anzeige, Daten) mit stabilem Datenwert ausgewaehlt.
        # EN: Do NOT translate the format names (A4, US Letter, …) themselves
        #     -- those are fixed, language-independent labels. Only the
        #     "Custom" entry needs translation, hence selected via
        #     addItem(display, data) with a stable data value.
        self._format_feld = QComboBox()
        for name in PAPIERFORMATE:
            self._format_feld.addItem(name, name)
        self._format_feld.addItem(self.tr(_BENUTZERDEFINIERT), _BENUTZERDEFINIERT)
        self._format_feld.setCurrentIndex(self._format_feld.findData("A4"))
        self._format_feld.currentIndexChanged.connect(self._format_geaendert)
        gruppe_layout.addWidget(self._format_feld)

        # DE: Automatik-Modus fuer Dokumente mit mehreren Abschnitten
        #     unterschiedlicher Zielgroesse (z. B. ein A3-Deckblatt vor
        #     A4-Innenseiten): statt EINES global gewaehlten Zielformats
        #     wird jede Seite einzeln vermessen und auf ihr eigenes
        #     naheliegendstes bekanntes Format normiert -- rundet dabei
        #     IMMER auf das relativ naechste Format, auch wenn keins
        #     wirklich gut passt (siehe naechstes_format()). Macht die
        #     Format-Auswahl darueber hinfaellig, daher deren Deaktivierung.
        # EN: Automatic mode for documents with several sections needing
        #     different target sizes (e.g. an A3 cover before A4 inner
        #     pages): instead of ONE globally chosen target format, each
        #     page is measured individually and normalized to its own
        #     nearest known format -- always rounds to the relatively
        #     closest format, even if none really fits well (see
        #     naechstes_format()). Makes the format selection above moot,
        #     hence disabling it.
        self._auto_format_feld = QCheckBox(
            self.tr("Format je Seite automatisch erkennen (A3, A4, … -- rundet auf das nächstliegende Format)")
        )
        self._auto_format_feld.toggled.connect(self._auto_format_umgeschaltet)
        gruppe_layout.addWidget(self._auto_format_feld)

        benutzerdefiniert_zeile = QHBoxLayout()
        self._breite_feld = QDoubleSpinBox()
        self._breite_feld.setPrefix(self.tr("Breite: "))
        self._breite_feld.valueChanged.connect(self._benutzerdefiniert_geaendert)
        self._hoehe_feld = QDoubleSpinBox()
        self._hoehe_feld.setPrefix(self.tr("Höhe: "))
        self._hoehe_feld.valueChanged.connect(self._benutzerdefiniert_geaendert)
        benutzerdefiniert_zeile.addWidget(self._breite_feld)
        benutzerdefiniert_zeile.addWidget(self._hoehe_feld)
        gruppe_layout.addLayout(benutzerdefiniert_zeile)
        self._breite_feld.setEnabled(False)
        self._hoehe_feld.setEnabled(False)
        self._masseinheit_feldformat_setzen(einstellungen.masseinheit())

        self._dpi_feld = QSpinBox()
        self._dpi_feld.setRange(50, 1200)
        self._dpi_feld.setValue(300)
        self._dpi_feld.setPrefix(self.tr("Ausgabeauflösung: "))
        self._dpi_feld.setSuffix(" dpi")
        gruppe_layout.addWidget(self._dpi_feld)

        self._rand_feld = QCheckBox(self.tr("Schwarze Ränder automatisch abschneiden"))
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
        self._btn_vorschlag = QPushButton(self.tr("Gemessene Größe übernehmen"))
        self._btn_vorschlag.setToolTip(
            self.tr("Die gemessene Größe der aktuellen Seite als Zielgröße oben einsetzen.")
        )
        self._btn_vorschlag.clicked.connect(self._vorschlag_uebernehmen)
        self._btn_vorschlag.setEnabled(False)
        vorschlag_zeile.addWidget(self._btn_vorschlag)
        gruppe_layout.addLayout(vorschlag_zeile)

        self._btn_anwenden = QPushButton(self.tr("Anwenden"))
        self._btn_anwenden.clicked.connect(self._anwenden)
        gruppe_layout.addWidget(self._btn_anwenden)

        uebersicht_gruppe = QGroupBox(self.tr("Gemessene Größe je Seite im gewählten Bereich"))
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

        self._format_geaendert(self._format_feld.currentIndex())
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

    # -- Masseinheit / measurement unit ------------------------------------

    def _masseinheit_feldformat_setzen(self, einheit: str) -> None:
        """DE: Nur Dezimalstellen/Schrittweite/Bereich/Suffix der Felder
            auf die Masseinheit einstellen -- ohne Werte oder abhaengige
            Anzeigen zu aktualisieren (fuer den Aufbau in __init__, bevor
            die uebrigen Widgets existieren).
        EN: Only configure the fields' decimals/step/range/suffix for the
            unit -- without refreshing values or dependent displays (for
            construction in __init__, before the other widgets exist)."""
        if einheit == "in":
            dezimalstellen, schritt, bereich = 2, 0.05, (0.4, 200.0)
        else:
            dezimalstellen, schritt, bereich = 1, 1.0, (10.0, 5000.0)
        for feld in (self._breite_feld, self._hoehe_feld):
            feld.blockSignals(True)
            feld.setDecimals(dezimalstellen)
            feld.setSingleStep(schritt)
            feld.setRange(*bereich)
            feld.setSuffix(f" {einheit}")
            feld.blockSignals(False)

    def _masseinheit_aktualisieren(self, einheit: str) -> None:
        """DE: Zahlenfelder auf die (neu) gewaehlte Masseinheit umstellen,
            ohne die kanonischen mm-Werte zu veraendern -- inkl. Neuaufbau
            aller abhaengigen Anzeigen (fuer Aenderungen zur Laufzeit).
        EN: Switch the spin boxes to the (newly) selected measurement
            unit, without changing the canonical mm values -- including
            refreshing all dependent displays (for runtime changes)."""
        self._masseinheit_feldformat_setzen(einheit)
        self._felder_anzeigen()
        self._auswahl_geaendert()

    def _felder_anzeigen(self) -> None:
        """DE: Breite/Hoehe-Felder aus den kanonischen mm-Werten in der
            aktuellen Masseinheit anzeigen (ohne Signale auszuloesen).
        EN: Display the width/height fields from the canonical mm values
            in the current measurement unit (without firing signals)."""
        einheit = einstellungen.masseinheit()
        for feld, mm_wert in ((self._breite_feld, self._breite_mm), (self._hoehe_feld, self._hoehe_mm)):
            feld.blockSignals(True)
            feld.setValue(mm_zu_einheit(mm_wert, einheit))
            feld.blockSignals(False)

    def _benutzerdefiniert_geaendert(self, _wert: float) -> None:
        """DE: Der Nutzer hat im Benutzerdefiniert-Modus ein Zahlenfeld
            von Hand geaendert -- in mm zurueckrechnen und als neuen
            kanonischen Zielwert merken.
        EN: The user manually changed a spin box in custom mode --
            convert back to mm and remember it as the new canonical
            target value."""
        einheit = einstellungen.masseinheit()
        self._breite_mm = einheit_zu_mm(self._breite_feld.value(), einheit)
        self._hoehe_mm = einheit_zu_mm(self._hoehe_feld.value(), einheit)

    # -- Format-Auswahl / format selection ---------------------------------

    def _format_geaendert(self, _index: int) -> None:
        text = self._format_feld.currentData()
        benutzerdefiniert = text == _BENUTZERDEFINIERT
        self._breite_feld.setEnabled(benutzerdefiniert and not self._auto_format_feld.isChecked())
        self._hoehe_feld.setEnabled(benutzerdefiniert and not self._auto_format_feld.isChecked())
        if not benutzerdefiniert:
            self._breite_mm, self._hoehe_mm = PAPIERFORMATE[text]
            self._felder_anzeigen()

    def _auto_format_umgeschaltet(self, aktiv: bool) -> None:
        """DE: Format-Dropdown und Benutzerdefiniert-Felder sperren/
            freigeben, je nachdem ob der Automatik-Modus aktiv ist -- im
            Automatik-Modus bestimmt jede Seite ihr Zielformat selbst.
        EN: Lock/unlock the format dropdown and custom fields depending
            on whether automatic mode is active -- in automatic mode
            each page determines its own target format."""
        self._format_feld.setEnabled(not aktiv)
        benutzerdefiniert = self._format_feld.currentData() == _BENUTZERDEFINIERT
        self._breite_feld.setEnabled(benutzerdefiniert and not aktiv)
        self._hoehe_feld.setEnabled(benutzerdefiniert and not aktiv)
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

    def _groesse_anzeigen(self, breite_mm: float, hoehe_mm: float) -> str:
        """DE: Eine Groesse in der aktuell gewaehlten Masseinheit formatieren.
        EN: Format a size in the currently selected measurement unit."""
        einheit = einstellungen.masseinheit()
        dezimalstellen = 2 if einheit == "in" else 1
        b = mm_zu_einheit(breite_mm, einheit)
        h = mm_zu_einheit(hoehe_mm, einheit)
        return self.tr("{0} × {1} {2}").format(f"{b:.{dezimalstellen}f}", f"{h:.{dezimalstellen}f}", einheit)

    # -- Randvorschau + Groessenuebersicht / border preview + size overview

    def _auswahl_geaendert(self) -> None:
        # DE: Ueberspringen, wenn nicht sichtbar -- siehe die ausfuehrliche
        #     Begruendung in rotate_tool.py's _auswahl_geaendert(). showEvent()
        #     holt die Vorschau nach, sobald das Werkzeug wieder sichtbar wird.
        #     Ebenso ueberspringen, waehrend _anwenden() laeuft: jedes
        #     einzelne Ersetzen einer Seite im Batch loest ueber Qts
        #     Auswahl-Signale einen Aufruf hier aus, der bis zu
        #     _MAX_UEBERSICHT_ZEILEN Seiten neu rendert -- reine
        #     Verschwendung, da der modale Fortschrittsdialog die
        #     Übersicht ohnehin verdeckt, und spuerbar langsam bei
        #     vielseitigen Dokumenten. _anwenden() ruft am Ende ohnehin
        #     einmal selbst auf, um die Anzeige aufzufrischen.
        # EN: Skip when not visible -- see the detailed rationale in
        #     rotate_tool.py's _auswahl_geaendert(). showEvent() catches the
        #     preview up once the tool becomes visible again. Also skip
        #     while _anwenden() is running: each individual page
        #     replacement in the batch triggers a call here via Qt's
        #     selection signals, which re-renders up to
        #     _MAX_UEBERSICHT_ZEILEN pages -- pure waste, since the modal
        #     progress dialog covers the overview anyway, and noticeably
        #     slow for many-page documents. _anwenden() calls this once by
        #     itself at the end regardless, to refresh the display.
        if not self.isVisible() or self._stapel_laeuft:
            return
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
                self._rand_info.setText(self.tr("Kein schwarzer Rand an der aktuellen Seite erkannt."))
            else:
                self._rand_info.setText(
                    self.tr("Erkannter Rand an der aktuellen Seite -- "
                           "links {0} %, oben {1} %, "
                           "rechts {2} %, unten {3} %.").format(
                        f"{links*100:.1f}", f"{oben*100:.1f}", f"{rechts*100:.1f}", f"{unten*100:.1f}"
                    )
                )
        else:
            self._rand_info.setText("")

        breite_mm, hoehe_mm = aktuelle_groesse_mm(wp, rand_abschneiden)
        vorschlag = naheliegendes_format(breite_mm, hoehe_mm)
        self._letzter_vorschlag = (vorschlag, breite_mm, hoehe_mm)
        self._btn_vorschlag.setEnabled(True)
        groesse_text = self._groesse_anzeigen(breite_mm, hoehe_mm)
        if vorschlag:
            self._vorschlag_info.setText(
                self.tr("Aktuelle Seite gemessen: {0} -- "
                       "entspricht ungefähr {1} "
                       "({2}).").format(
                    groesse_text, vorschlag, self._groesse_anzeigen(*PAPIERFORMATE[vorschlag])
                )
            )
        else:
            self._vorschlag_info.setText(
                self.tr("Aktuelle Seite gemessen: {0} -- "
                       "entspricht keinem bekannten Papierformat.").format(groesse_text)
            )

    def _uebersicht_aktualisieren(self) -> None:
        elemente = self._ziel_elemente()
        if not elemente:
            self._uebersicht_info.setText(self.tr("Keine Seiten im gewählten Bereich."))
            return
        rand_abschneiden = self._rand_feld.isChecked()
        automatik = self._auto_format_feld.isChecked()
        zeilen = []
        for item in elemente[:_MAX_UEBERSICHT_ZEILEN]:
            wp = item.data(Qt.ItemDataRole.UserRole)
            breite_mm, hoehe_mm = aktuelle_groesse_mm(wp, rand_abschneiden)
            zeile = self.tr("{0}. {1}").format(self.liste.row(item) + 1, self._groesse_anzeigen(breite_mm, hoehe_mm))
            if automatik:
                # DE: Im Automatik-Modus wird IMMER normiert (kein "passt zu
                #     keinem Format" moeglich) -- daher hier das tatsaechliche
                #     Ziel zeigen, nicht nur eine unverbindliche Vermutung.
                # EN: In automatic mode, normalization always happens (no
                #     "matches no format" possible) -- so show the actual
                #     target here, not just a non-committal guess.
                ziel = naechstes_format(breite_mm, hoehe_mm)
                zeile += self.tr(" → wird auf {0} normiert").format(ziel)
            else:
                vorschlag = naheliegendes_format(breite_mm, hoehe_mm)
                if vorschlag:
                    zeile += self.tr(" (≈ {0})").format(vorschlag)
            zeilen.append(zeile)
        if len(elemente) > _MAX_UEBERSICHT_ZEILEN:
            zeilen.append(self.tr("… und {0} weitere Seite(n).").format(len(elemente) - _MAX_UEBERSICHT_ZEILEN))
        self._uebersicht_info.setText("\n".join(zeilen))

    def _vorschlag_uebernehmen(self) -> None:
        if self._letzter_vorschlag is None:
            return
        vorschlag, breite_mm, hoehe_mm = self._letzter_vorschlag
        if vorschlag:
            self._format_feld.setCurrentIndex(self._format_feld.findData(vorschlag))
        else:
            self._breite_mm, self._hoehe_mm = breite_mm, hoehe_mm
            self._format_feld.setCurrentIndex(self._format_feld.findData(_BENUTZERDEFINIERT))
            self._felder_anzeigen()

    # -- Anwenden / apply ----------------------------------------------------

    def _anwenden(self) -> None:
        ziel = self._ziel_elemente()
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Auswahl"), self.tr("Bitte zuerst Seiten in der Liste links auswählen.")
            )
            return

        automatik = self._auto_format_feld.isChecked()
        breite_mm = self._breite_mm
        hoehe_mm = self._hoehe_mm
        dpi = float(self._dpi_feld.value())
        rand_abschneiden = self._rand_feld.isChecked()
        arbeits_unterordner = arbeitsordner.pfad() / uuid.uuid4().hex

        anzeige = Fortschrittsanzeige(self, self.tr("Seiten werden normiert …"), len(ziel))
        self._stapel_laeuft = True
        try:
            with self.liste.stapelverarbeitung():
                for i, item in enumerate(ziel, start=1):
                    wp = item.data(Qt.ItemDataRole.UserRole)
                    if automatik:
                        # DE: Je Seite ihr eigenes naheliegendstes Format
                        #     bestimmen -- nicht das global gewaehlte
                        #     Zielformat verwenden. So normiert ein einziger
                        #     Durchlauf ein Dokument mit z. B. A3-Deckblatt
                        #     und A4-Innenseiten jeweils richtig. Nutzt
                        #     seite_automatisch_normieren() statt getrennt
                        #     aktuelle_groesse_mm() + seite_normieren()
                        #     aufzurufen -- Letzteres wuerde jede Seite
                        #     ZWEIMAL komplett rendern (einmal zum Messen,
                        #     einmal zum eigentlichen Normieren), was bei
                        #     vielseitigen Dokumenten spuerbar langsam war.
                        # EN: Determine each page's own nearest format --
                        #     don't use the globally chosen target format.
                        #     This way a single pass correctly normalizes a
                        #     document with e.g. an A3 cover and A4 inner
                        #     pages. Uses seite_automatisch_normieren()
                        #     instead of separately calling
                        #     aktuelle_groesse_mm() + seite_normieren() --
                        #     the latter would fully render each page
                        #     TWICE (once to measure, once to actually
                        #     normalize), which was noticeably slow for
                        #     many-page documents.
                        bild, ziel_dpi, _format = seite_automatisch_normieren(wp, dpi, rand_abschneiden)
                    else:
                        bild, ziel_dpi = seite_normieren(wp, breite_mm, hoehe_mm, dpi, rand_abschneiden)
                    source = bild_materialisieren(bild, ziel_dpi, arbeits_unterordner, f"normiert_{uuid.uuid4().hex[:8]}")
                    self.liste.ersetzen(item, [source])
                    anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            self._stapel_laeuft = False
            anzeige.schliessen()

        self._auswahl_geaendert()
        if automatik:
            QMessageBox.information(
                self, self.tr("Fertig"),
                self.tr("{0} Seite(n) je auf ihr eigenes erkanntes Format normiert.").format(len(ziel))
            )
        else:
            QMessageBox.information(
                self, self.tr("Fertig"),
                self.tr("{0} Seite(n) auf {1} normiert.").format(len(ziel), self._groesse_anzeigen(breite_mm, hoehe_mm))
            )
