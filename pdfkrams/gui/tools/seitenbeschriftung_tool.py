"""
DE: Werkzeug "Seiten benennen": vergibt PDF-native Seitenbeschriftungen
    (page labels) -- die Bezeichnung, die z. B. Acrobat im Seiten-
    Navigator statt der reinen Blattposition anzeigt. Unabhängig von der
    tatsächlichen Blattreihenfolge, z. B. um Umschlagseiten am Anfang und
    Ende eines Buchs in römischen Ziffern (I, II, …) zu benennen, während
    dazwischen der Buchblock in arabischen Ziffern (1, 2, …) läuft.
    Seite links auswählen, die eine neue Gruppe beginnen soll, Stil/
    Präfix/Startnummer wählen und "Gruppe hier setzen" -- jede Seite ohne
    eigene Markierung setzt einfach die Zählung der vorherigen Gruppe
    fort. Die Übersicht unten zeigt alle bislang definierten Gruppen und
    erlaubt es, eine davon als Vorlage auf eine andere (auch weiter
    hinten liegende) Seite fortzusetzen -- genau für den Umschlag-Fall.

EN: "Name pages" tool: assigns PDF-native page labels -- the designation
    e.g. Acrobat shows in its page navigator instead of the raw sheet
    position. Independent of the actual sheet order, e.g. to label cover
    pages at the start and end of a book in roman numerals (I, II, …)
    while the book block in between runs in arabic numerals (1, 2, …).
    Select a page on the left that should start a new group, choose
    style/prefix/start number, and "Set group here" -- any page without
    its own marker simply continues the previous group's count. The
    overview below shows every group defined so far and lets you use one
    as a template to continue on another (even a later) page -- exactly
    for the cover case.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.document import WorkingPage
from pdfkrams.core.seitenbeschriftung import STILE, Beschriftungsgruppe, gruppen_berechnen
from pdfkrams.gui.widgets.page_list import PageListWidget


class SeitenbeschriftungToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zuweisen von PDF-Seitenbeschriftungen.
    EN: GUI page for assigning PDF page labels.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste
        # DE: Zuletzt in der Uebersicht angeklickte Gruppe -- Vorlage fuer
        #     den "Fortsetzen"-Knopf.
        # EN: Last group clicked in the overview -- template for the
        #     "continue" button.
        self._vorlage_gruppe: Beschriftungsgruppe | None = None

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())
        self.liste.geaendert.connect(self._uebersicht_aktualisieren)

        hinweis = QLabel(
            self.tr("Vergibt PDF-native Seitenbeschriftungen (wie in Acrobats Seiten-"
                   "Navigator) -- unabhängig von der tatsächlichen Blattreihenfolge, z. B. "
                   "Umschlagseiten in römischen Ziffern (I, II, …) vor und nach einem in "
                   "arabischen Ziffern (1, 2, …) durchnummerierten Buchblock. Seite links "
                   "auswählen, die eine neue Gruppe beginnen soll, Stil/Präfix/Startnummer "
                   "wählen und „Gruppe hier setzen“ klicken. Seiten ohne eigene Markierung "
                   "setzen einfach die Zählung der vorherigen Gruppe fort.")
        )
        hinweis.setWordWrap(True)

        bereich_zeile = QHBoxLayout()
        self._von_feld = QSpinBox()
        self._von_feld.setPrefix(self.tr("Von Seite "))
        self._von_feld.setMinimum(1)
        self._bis_feld = QSpinBox()
        self._bis_feld.setPrefix(self.tr("bis Seite "))
        self._bis_feld.setMinimum(1)
        btn_bereich_markieren = QPushButton(self.tr("Bereich in der Liste markieren"))
        btn_bereich_markieren.setToolTip(
            self.tr("Praktisch bei langen Bereichen, statt einzeln durchzuscrollen -- "
                   "markiert nur, die eigentliche Gruppe entsteht erst mit „Gruppe hier setzen“.")
        )
        btn_bereich_markieren.clicked.connect(self._bereich_markieren)
        bereich_zeile.addWidget(self._von_feld)
        bereich_zeile.addWidget(self._bis_feld)
        bereich_zeile.addWidget(btn_bereich_markieren)

        eingabe_gruppe = QGroupBox(self.tr("Neue Gruppe auf der aktuellen Seite beginnen"))
        eingabe_layout = QVBoxLayout(eingabe_gruppe)
        eingabe_layout.addLayout(bereich_zeile)

        stil_zeile = QHBoxLayout()
        self._stil_feld = QComboBox()
        for code, name in STILE.items():
            # DE: self.tr(name) -- Uebersetzung wird von Hand in der .ts
            #     ergaenzt (siehe main_window.py fuer denselben Ansatz).
            # EN: self.tr(name) -- translation added by hand to the .ts
            #     (see main_window.py for the same approach).
            self._stil_feld.addItem(self.tr(name), code)
        self._stil_feld.currentIndexChanged.connect(self._stil_geaendert)
        self._praefix_feld = QLineEdit()
        self._praefix_feld.setPlaceholderText(self.tr("Präfix, z. B. „Anhang “ (optional)"))
        self._start_feld = QSpinBox()
        self._start_feld.setPrefix(self.tr("Start bei "))
        self._start_feld.setRange(1, 99999)
        stil_zeile.addWidget(self._stil_feld)
        stil_zeile.addWidget(self._praefix_feld, 1)
        stil_zeile.addWidget(self._start_feld)
        eingabe_layout.addLayout(stil_zeile)

        knopf_zeile = QHBoxLayout()
        btn_setzen = QPushButton(self.tr("Gruppe hier setzen"))
        btn_setzen.clicked.connect(self._gruppe_setzen)
        btn_fortsetzen = QPushButton(self.tr("Vorlage hier fortsetzen"))
        btn_fortsetzen.setToolTip(
            self.tr("Übernimmt Stil und Präfix der unten in der Übersicht ausgewählten "
                   "Gruppe, mit der passenden Startnummer, um sie hier fortlaufend "
                   "weiterzuführen -- z. B. um Umschlagseiten am Anfang UND Ende eines "
                   "Buchblocks einheitlich fortlaufend zu benennen.")
        )
        btn_fortsetzen.clicked.connect(self._fortsetzen)
        btn_entfernen = QPushButton(self.tr("Markierung hier entfernen"))
        btn_entfernen.clicked.connect(self._entfernen)
        knopf_zeile.addWidget(btn_setzen)
        knopf_zeile.addWidget(btn_fortsetzen)
        knopf_zeile.addWidget(btn_entfernen)
        eingabe_layout.addLayout(knopf_zeile)

        self._info = QLabel()
        self._info.setWordWrap(True)
        self._info.setStyleSheet("color: gray;")
        eingabe_layout.addWidget(self._info)

        uebersicht_titel = QLabel(
            self.tr("Bisher definierte Gruppen (anklicken springt zur Seite, lädt sie zum "
                   "Bearbeiten und als Vorlage zum Fortsetzen):")
        )
        self._uebersicht = QListWidget()
        self._uebersicht.itemClicked.connect(self._gruppe_geklickt)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(eingabe_gruppe)
        layout.addWidget(uebersicht_titel)
        layout.addWidget(self._uebersicht, 1)

        self._auswahl_geaendert()
        self._uebersicht_aktualisieren()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        # DE: Auch beim Werkzeugwechsel aktualisieren -- siehe rotate_tool.py
        #     fuer die ausfuehrliche Begruendung (gleiches Muster ueberall).
        # EN: Also refresh when switching tools -- see rotate_tool.py for the
        #     full rationale (same pattern everywhere).
        super().showEvent(event)
        self._auswahl_geaendert()

    # -- Auswahl / selection ------------------------------------------------

    def _stil_geaendert(self, _index: int) -> None:
        # DE: Startnummer ist bei Stil "kein" (nur Praefix) wirkungslos.
        # EN: Start number has no effect with style "none" (prefix only).
        self._start_feld.setEnabled(self._stil_feld.currentData() != "")

    def _auswahl_geaendert(self) -> None:
        if not self.isVisible():
            return
        item = self.liste.currentItem()
        if item is None:
            self._info.setText(self.tr("Keine Seite ausgewählt."))
            return

        zeile = self.liste.row(item)
        anzahl = max(1, self.liste.count())
        self._von_feld.blockSignals(True)
        self._bis_feld.blockSignals(True)
        self._von_feld.setMaximum(anzahl)
        self._bis_feld.setMaximum(anzahl)
        self._von_feld.setValue(zeile + 1)
        gewaehlt = self.liste.selectedItems()
        bis_zeile = max((self.liste.row(it) for it in gewaehlt), default=zeile)
        self._bis_feld.setValue(max(zeile, bis_zeile) + 1)
        self._von_feld.blockSignals(False)
        self._bis_feld.blockSignals(False)

        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        if wp.beschriftung_stil is not None:
            self._stil_feld.setCurrentIndex(self._stil_feld.findData(wp.beschriftung_stil))
            self._praefix_feld.setText(wp.beschriftung_praefix)
            self._start_feld.setValue(wp.beschriftung_start)
            self._info.setText(
                self.tr("Seite {0} beginnt bereits eine Gruppe -- Werte oben übernommen, "
                       "„Gruppe hier setzen“ überschreibt sie.").format(zeile + 1)
            )
        else:
            self._info.setText(
                self.tr("Seite {0} beginnt noch keine Gruppe -- setzt einfach die Zählung "
                       "der vorherigen Gruppe fort (falls vorhanden).").format(zeile + 1)
            )

    def _bereich_markieren(self) -> None:
        if self.liste.count() == 0:
            return
        von = self._von_feld.value() - 1
        bis = self._bis_feld.value() - 1
        if bis < von:
            von, bis = bis, von
        self.liste.clearSelection()
        for i in range(von, bis + 1):
            self.liste.item(i).setSelected(True)
        self.liste.setCurrentRow(von)

    # -- Gruppen setzen/entfernen/fortsetzen --------------------------------

    def _gruppe_setzen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        self.liste.vor_aenderung_sichern()
        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        wp.beschriftung_stil = self._stil_feld.currentData()
        wp.beschriftung_praefix = self._praefix_feld.text()
        wp.beschriftung_start = self._start_feld.value()
        self.liste.item_aktualisieren(item)
        self._uebersicht_aktualisieren()
        self._auswahl_geaendert()

    def _entfernen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        self.liste.vor_aenderung_sichern()
        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        wp.beschriftung_stil = None
        wp.beschriftung_praefix = ""
        wp.beschriftung_start = 1
        self.liste.item_aktualisieren(item)
        self._uebersicht_aktualisieren()
        self._auswahl_geaendert()

    def _fortsetzen(self) -> None:
        if self._vorlage_gruppe is None:
            QMessageBox.information(
                self, self.tr("Keine Vorlage gewählt"),
                self.tr("Zuerst unten in der Übersicht eine Gruppe anklicken, die "
                       "fortgesetzt werden soll.")
            )
            return
        self._stil_feld.setCurrentIndex(self._stil_feld.findData(self._vorlage_gruppe.stil))
        self._praefix_feld.setText(self._vorlage_gruppe.praefix)
        self._start_feld.setValue(self._vorlage_gruppe.naechste_nummer)
        self._gruppe_setzen()

    # -- Uebersicht / overview --------------------------------------------

    def _uebersicht_aktualisieren(self) -> None:
        self._uebersicht.clear()
        for gruppe in gruppen_berechnen(self.liste.seiten()):
            bereich = (
                self.tr("Seite {0}").format(gruppe.start_index + 1) if gruppe.anzahl == 1
                else self.tr("Seiten {0}–{1}").format(gruppe.start_index + 1, gruppe.end_index + 1)
            )
            text = self.tr("{0}: {1}–{2} ({3})").format(
                bereich, gruppe.erste_beschriftung, gruppe.letzte_beschriftung,
                self.tr(STILE.get(gruppe.stil, gruppe.stil)),
            )
            eintrag = QListWidgetItem(text)
            eintrag.setData(Qt.ItemDataRole.UserRole, gruppe)
            self._uebersicht.addItem(eintrag)

    def _gruppe_geklickt(self, eintrag: QListWidgetItem) -> None:
        gruppe: Beschriftungsgruppe = eintrag.data(Qt.ItemDataRole.UserRole)
        self._vorlage_gruppe = gruppe
        self.liste.setCurrentRow(gruppe.start_index)
