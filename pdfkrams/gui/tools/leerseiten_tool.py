"""
DE: Werkzeug "Seiten entfernen": zwei Wege, Seiten aus der Liste zu
    entfernen. 1. Manuell: die in der Liste links markierten Seiten sofort
    entfernen, ganz ohne Suche -- fuer den Fall, dass man ohnehin schon
    weiss, welche Seiten weg sollen. 2. Automatisch vorgeschlagen: sucht im
    gewählten Bereich nach wahrscheinlich leeren Seiten (per Tinte-Anteil,
    siehe core/leerseiten.py) -- typisch beim automatisierten Scannen mit
    Einzug (Duplex mit gelegentlich unbedruckter Rückseite, leere
    Trennblätter). Findet dabei nur VORSCHLÄGE, löscht nichts automatisch:
    die gefundenen Seiten erscheinen in einer Übersicht mit Häkchen (alle
    vorausgewählt), zum Abwählen einzelner Seiten vor dem tatsächlichen
    Entfernen.

EN: "Remove pages" tool: two ways to remove pages from the list.
    1. Manual: immediately remove the pages marked in the list on the
    left, no search involved -- for when you already know which pages
    should go. 2. Automatically suggested: searches the selected scope for
    likely blank pages (via ink share, see core/leerseiten.py) -- typical
    with automated ADF scanning (duplex with an occasionally unprinted
    back side, blank separator sheets). Only finds SUGGESTIONS, doesn't
    delete anything automatically: the pages found appear in an overview
    with checkboxes (all preselected), so individual pages can be
    deselected before actually removing them.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.leerseiten import STANDARD_HOECHSTANTEIL, STANDARD_SCHWELLWERT, ist_wahrscheinlich_leer
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"


class LeerseitenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Suchen und Entfernen wahrscheinlich leerer Seiten.
    EN: GUI page for finding and removing likely blank pages.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        # DE: Manuelles Entfernen -- direkt die markierten Seiten loeschen,
        #     ganz ohne Suche. Ruft dieselbe Methode auf wie der
        #     "Auswahl entfernen"-Knopf im Datei-Panel links -- hier nur
        #     zusaetzlich sichtbar, weil er inhaltlich zu diesem Werkzeug
        #     passt.
        # EN: Manual removal -- directly delete the marked pages, no
        #     search involved. Calls the same method as the "Remove
        #     selection" button in the file panel on the left -- just
        #     also shown here since it fits this tool's purpose.
        manuell_hinweis = QLabel(
            self.tr("In der Liste links markierte Seiten direkt entfernen, ohne Suche.")
        )
        manuell_hinweis.setWordWrap(True)
        btn_manuell_entfernen = QPushButton(self.tr("Markierte Seiten jetzt entfernen"))
        btn_manuell_entfernen.clicked.connect(self.liste.ausgewaehlte_entfernen)

        manuell_gruppe = QGroupBox(self.tr("Manuell entfernen"))
        manuell_layout = QVBoxLayout(manuell_gruppe)
        manuell_layout.addWidget(manuell_hinweis)
        manuell_layout.addWidget(btn_manuell_entfernen)

        trenner = QFrame()
        trenner.setFrameShape(QFrame.Shape.HLine)

        hinweis = QLabel(
            self.tr("Sucht Seiten, die praktisch nichts als Tinte enthalten -- typisch bei "
                   "automatisiertem Scannen mit Einzug (unbedruckte Rückseiten, leere "
                   "Trennblätter). Findet nur Vorschläge: unten abwählen, was tatsächlich "
                   "keine Leerseite ist, bevor entfernt wird.")
        )
        hinweis.setWordWrap(True)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)
        # DE: Anders als bei den meisten Werkzeugen ist "Alle Seiten" hier
        #     die sinnvollste Vorgabe -- man sucht typischerweise im
        #     gesamten frisch geladenen Stapel nach Leerseiten.
        # EN: Unlike most tools, "All pages" is the most sensible default
        #     here -- one typically searches the whole freshly loaded
        #     batch for blank pages.
        self._geltungsbereich.setCurrentIndex(self._geltungsbereich.findData(_ALLE_SEITEN))

        gruppe = QGroupBox(self.tr("Leerseiten suchen in:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        einstellungen_zeile = QHBoxLayout()
        self._schwellwert_feld = QSpinBox()
        self._schwellwert_feld.setRange(0, 255)
        self._schwellwert_feld.setValue(STANDARD_SCHWELLWERT)
        self._schwellwert_feld.setPrefix(self.tr("Schwellwert: "))
        self._schwellwert_feld.setToolTip(
            self.tr("Pixel dunkler als dieser Wert gelten als Tinte (0-255).")
        )
        self._hoechstanteil_feld = QDoubleSpinBox()
        self._hoechstanteil_feld.setRange(0.0, 10.0)
        self._hoechstanteil_feld.setDecimals(2)
        self._hoechstanteil_feld.setSingleStep(0.1)
        self._hoechstanteil_feld.setValue(STANDARD_HOECHSTANTEIL * 100)
        self._hoechstanteil_feld.setSuffix(" %")
        self._hoechstanteil_feld.setPrefix(self.tr("Höchstens: "))
        self._hoechstanteil_feld.setToolTip(
            self.tr("Seiten mit höchstens diesem Tinte-Anteil gelten als wahrscheinlich leer.")
        )
        einstellungen_zeile.addWidget(self._schwellwert_feld)
        einstellungen_zeile.addWidget(self._hoechstanteil_feld)
        gruppe_layout.addLayout(einstellungen_zeile)

        self._btn_suchen = QPushButton(self.tr("Leerseiten suchen"))
        self._btn_suchen.clicked.connect(self._suchen)
        gruppe_layout.addWidget(self._btn_suchen)

        self._ergebnis_info = QLabel()
        self._ergebnis_info.setWordWrap(True)

        self._ergebnis_liste = QListWidget()

        self._btn_entfernen = QPushButton(self.tr("Ausgewählte entfernen"))
        self._btn_entfernen.setEnabled(False)
        self._btn_entfernen.clicked.connect(self._entfernen)

        layout = QVBoxLayout(self)
        layout.addWidget(manuell_gruppe)
        layout.addWidget(trenner)
        layout.addWidget(hinweis)
        layout.addWidget(gruppe)
        layout.addWidget(self._ergebnis_info)
        layout.addWidget(self._ergebnis_liste, 1)
        layout.addWidget(self._btn_entfernen)

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

    # -- Suchen / search ------------------------------------------------------

    def _suchen(self) -> None:
        ziel = self._ziel_elemente()
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Auswahl"), self.tr("Bitte zuerst Seiten in der Liste links auswählen.")
            )
            return

        schwellwert = self._schwellwert_feld.value()
        hoechstanteil = self._hoechstanteil_feld.value() / 100.0

        self._ergebnis_liste.clear()
        self._btn_entfernen.setEnabled(False)

        anzeige = Fortschrittsanzeige(self, self.tr("Seiten werden geprüft …"), len(ziel))
        gefunden: list[tuple[QListWidgetItem, float]] = []
        try:
            for i, item in enumerate(ziel, start=1):
                wp = item.data(Qt.ItemDataRole.UserRole)
                leer, anteil = ist_wahrscheinlich_leer(wp, schwellwert, hoechstanteil)
                if leer:
                    gefunden.append((item, anteil))
                anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()

        for item, anteil in gefunden:
            zeile = self.liste.row(item) + 1
            eintrag = QListWidgetItem(
                self.tr("Seite {0}: {1} ({2:.2f} % Tinte)").format(zeile, item.data(Qt.ItemDataRole.UserRole).source.label, anteil * 100)
            )
            eintrag.setFlags(eintrag.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            eintrag.setCheckState(Qt.CheckState.Checked)
            eintrag.setData(Qt.ItemDataRole.UserRole, item)
            self._ergebnis_liste.addItem(eintrag)

        self._ergebnis_info.setText(
            self.tr("{0} von {1} geprüften Seiten wahrscheinlich leer.").format(len(gefunden), len(ziel))
        )
        self._btn_entfernen.setEnabled(bool(gefunden))

    # -- Entfernen / remove ----------------------------------------------------

    def _entfernen(self) -> None:
        ausgewaehlt = [
            self._ergebnis_liste.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._ergebnis_liste.count())
            if self._ergebnis_liste.item(i).checkState() == Qt.CheckState.Checked
        ]
        if not ausgewaehlt:
            return

        self.liste.clearSelection()
        for item in ausgewaehlt:
            item.setSelected(True)
        self.liste.ausgewaehlte_entfernen()

        self._ergebnis_liste.clear()
        self._btn_entfernen.setEnabled(False)
        self._ergebnis_info.setText(self.tr("{0} Seite(n) entfernt.").format(len(ausgewaehlt)))
