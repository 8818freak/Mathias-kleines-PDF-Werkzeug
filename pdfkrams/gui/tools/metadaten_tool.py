"""
DE: Werkzeug "Metadaten bearbeiten" -- anders als alle anderen Werkzeuge
    gilt hier ein einziger Satz Angaben fuer das GESAMTE Dokument, nicht
    pro Seite: Titel, Autor, Anbieter, Produkt, Version, Releasedatum und
    Stichwoerter. Deshalb kein Geltungsbereich (Aktuelle Seite/Ausgewaehlt/
    Alle Seiten) und keine Vorschau-Miniatur wie bei den anderen
    Werkzeugen -- stattdessen eine Textvorschau, die zeigt, wie die
    eingegebenen Felder tatsaechlich in die vier PDF-Standardfelder
    (Titel/Autor/Thema/Stichwoerter) einfliessen (siehe core/metadaten.py).
    Aenderungen werden sofort auf der geteilten Dateiliste gespeichert --
    kein "Anwenden"-Knopf, da hier nichts verarbeitet werden muss.

EN: "Edit metadata" tool -- unlike every other tool, a single set of
    values applies to the WHOLE document here, not per page: title,
    author, provider, product, version, release date, and keywords.
    Hence no scope selector (current page/selected/all pages) and no
    thumbnail preview like the other tools -- instead a text preview
    showing how the entered fields actually flow into the four standard
    PDF fields (title/author/subject/keywords, see core/metadaten.py).
    Changes are saved immediately on the shared file list -- no "Apply"
    button, since nothing needs processing here.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.widgets.page_list import PageListWidget


class MetadatenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer die dokumentweiten PDF-Metadaten.
    EN: GUI page for the document-wide PDF metadata.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        hinweis = QLabel(
            self.tr("Gilt für das gesamte Dokument (nicht pro Seite). PDF kennt nur Titel, Autor, Thema und "
                   "Stichwörter als feste Felder -- Produkt, Version und Releasedatum werden deshalb "
                   "automatisch mit in die Stichwörter eingewoben (siehe Vorschau unten). Wird beim "
                   "Speichern automatisch übernommen.")
        )
        hinweis.setWordWrap(True)

        rohdaten = self.liste.dokument_metadaten

        self._titel_feld = QLineEdit(rohdaten["titel"])
        self._titel_feld.textChanged.connect(lambda t: self._feld_geaendert("titel", t))

        self._autor_feld = QLineEdit(rohdaten["autor"])
        self._autor_feld.textChanged.connect(lambda t: self._feld_geaendert("autor", t))

        # DE: Anbieter -- vorbelegt aus den Einstellungen (Standard-
        #     Anbieter, sonst zuletzt verwendeter), falls fuer dieses
        #     Dokument noch keiner eingetragen wurde.
        # EN: Provider -- prefilled from Preferences (default provider,
        #     else the most recently used one), unless this document
        #     already has one entered.
        if not rohdaten["anbieter"]:
            rohdaten["anbieter"] = einstellungen.anbieter_standard() or einstellungen.anbieter_letzter()
        self._anbieter_feld = QLineEdit(rohdaten["anbieter"])
        self._anbieter_feld.textChanged.connect(self._anbieter_geaendert)

        self._produkt_feld = QLineEdit(rohdaten["produkt"])
        self._produkt_feld.setPlaceholderText(self.tr("z. B. Gigaset E290"))
        self._produkt_feld.textChanged.connect(lambda t: self._feld_geaendert("produkt", t))

        self._version_feld = QLineEdit(rohdaten["version"])
        self._version_feld.setPlaceholderText(self.tr("z. B. 1.2"))
        self._version_feld.textChanged.connect(lambda t: self._feld_geaendert("version", t))

        self._datum_ankreuzfeld = QCheckBox(self.tr("Datum angeben:"))
        self._datum_feld = QDateEdit(date.today())
        self._datum_feld.setCalendarPopup(True)
        self._datum_feld.setEnabled(False)
        if rohdaten["releasedatum"]:
            self._datum_ankreuzfeld.setChecked(True)
            self._datum_feld.setEnabled(True)
            self._datum_feld.setDate(date.fromisoformat(rohdaten["releasedatum"]))
        self._datum_ankreuzfeld.toggled.connect(self._datum_umgeschaltet)
        self._datum_feld.dateChanged.connect(lambda _d: self._datum_umgeschaltet(True))
        datum_zeile = QHBoxLayout()
        datum_zeile.addWidget(self._datum_ankreuzfeld)
        datum_zeile.addWidget(self._datum_feld)

        self._stichwoerter_feld = QLineEdit(rohdaten["stichwoerter"])
        self._stichwoerter_feld.setPlaceholderText(self.tr("frei, durch Komma getrennt"))
        self._stichwoerter_feld.textChanged.connect(lambda t: self._feld_geaendert("stichwoerter", t))

        formular = QFormLayout()
        formular.addRow(self.tr("Titel:"), self._titel_feld)
        formular.addRow(self.tr("Autor:"), self._autor_feld)
        formular.addRow(self.tr("Anbieter:"), self._anbieter_feld)
        formular.addRow(self.tr("Produkt:"), self._produkt_feld)
        formular.addRow(self.tr("Version:"), self._version_feld)
        formular.addRow("", datum_zeile)
        formular.addRow(self.tr("Stichwörter:"), self._stichwoerter_feld)

        self._vorschau_titel = QLabel(self.tr("Vorschau -- so landet es im PDF:"))
        self._vorschau = QLabel()
        self._vorschau.setWordWrap(True)
        self._vorschau.setStyleSheet("color: gray;")

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addLayout(formular)
        layout.addWidget(self._vorschau_titel)
        layout.addWidget(self._vorschau)
        layout.addStretch(1)

        self._vorschau_aktualisieren()

    # -- Feldaenderungen / field changes ------------------------------------

    def _feld_geaendert(self, feld: str, wert: str) -> None:
        self.liste.dokument_metadaten[feld] = wert
        self._vorschau_aktualisieren()

    def _anbieter_geaendert(self, wert: str) -> None:
        self._feld_geaendert("anbieter", wert)
        einstellungen.anbieter_letzter_setzen(wert)

    def _datum_umgeschaltet(self, gesetzt: bool) -> None:
        self._datum_feld.setEnabled(gesetzt)
        wert = self._datum_feld.date().toPython().isoformat() if gesetzt else ""
        self._feld_geaendert("releasedatum", wert)

    # -- Vorschau / preview ---------------------------------------------------

    def _vorschau_aktualisieren(self) -> None:
        felder = self.liste.pdf_metadaten_felder()
        if not felder:
            self._vorschau.setText(self.tr("Noch keine Angaben -- die PDF-Metadaten bleiben leer."))
            return
        beschriftung = {
            "title": self.tr("Titel"),
            "author": self.tr("Autor"),
            "subject": self.tr("Thema"),
            "keywords": self.tr("Stichwörter"),
        }
        zeilen = [f"{beschriftung[schluessel]}: {wert}" for schluessel, wert in felder.items()]
        self._vorschau.setText("\n".join(zeilen))
