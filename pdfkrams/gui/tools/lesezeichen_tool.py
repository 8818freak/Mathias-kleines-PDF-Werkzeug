"""
DE: Werkzeug "Lesezeichen setzen": fuer Broschueren/Buecher, die man
    ohnehin schon Seite fuer Seite durchgeht -- jeder Seite optional einen
    Kapitel- oder Unterkapitel-Titel geben, der beim Speichern automatisch
    zu einem PDF-Lesezeichen/Inhaltsverzeichnis (Outline) wird. Die
    Uebersicht unten zeigt alle bislang gesetzten Lesezeichen in
    Seitenreihenfolge; ein Klick darauf springt zur jeweiligen Seite.

EN: "Set bookmarks" tool: for booklets/books one already goes through
    page by page anyway -- optionally give each page a chapter or
    sub-chapter title, which automatically becomes a PDF bookmark/table
    of contents (outline) when saving. The overview below shows every
    bookmark set so far in page order; clicking one jumps to that page.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.document import WorkingPage
from pdfkrams.gui.widgets.page_list import PageListWidget, vorschau_pixmap

_VORSCHAU_GROESSE = 900

_KAPITEL = 1
_UNTERKAPITEL = 2


class LesezeichenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Zuweisen von Lesezeichen-Titeln pro Seite.
    EN: GUI page for assigning bookmark titles per page.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())
        self.liste.geaendert.connect(self._uebersicht_aktualisieren)

        hinweis = QLabel(
            self.tr("Für Broschüren/Bücher: jede Seite links auswählen, die ein Kapitel oder "
                   "Unterkapitel beginnt, und hier einen Titel eintragen. Wird beim Speichern "
                   "automatisch zu einem Lesezeichen/Inhaltsverzeichnis in der PDF-Datei.")
        )
        hinweis.setWordWrap(True)

        self._vorschau = QLabel(self.tr("Keine Seite ausgewählt"))
        self._vorschau.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vorschau.setStyleSheet("background: #2b2b2b; color: #aaaaaa;")
        self._vorschau.setMinimumHeight(240)
        self._vorschau.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        zeile = QHBoxLayout()
        self._titel_feld = QLineEdit()
        self._titel_feld.setPlaceholderText(self.tr("Titel, z. B. „Kapitel 3 – Anschlüsse“"))
        self._ebene_feld = QComboBox()
        self._ebene_feld.addItem(self.tr("Kapitel"), _KAPITEL)
        self._ebene_feld.addItem(self.tr("Unterkapitel"), _UNTERKAPITEL)
        btn_setzen = QPushButton(self.tr("Setzen && weiter"))
        btn_setzen.clicked.connect(self._setzen)
        btn_entfernen = QPushButton(self.tr("Entfernen"))
        btn_entfernen.clicked.connect(self._entfernen)
        zeile.addWidget(self._titel_feld, 1)
        zeile.addWidget(self._ebene_feld)
        zeile.addWidget(btn_setzen)
        zeile.addWidget(btn_entfernen)

        uebersicht_titel = QLabel(self.tr("Bisher gesetzte Lesezeichen (anklicken springt zur Seite):"))
        self._uebersicht = QListWidget()
        self._uebersicht.itemClicked.connect(self._zu_seite_springen)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(self._vorschau, 1)
        layout.addLayout(zeile)
        layout.addWidget(uebersicht_titel)
        layout.addWidget(self._uebersicht)

        self._auswahl_geaendert()
        self._uebersicht_aktualisieren()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        # DE: Vorschau auch beim Werkzeugwechsel aktualisieren, nicht nur
        #     bei geaenderter Auswahl -- siehe rotate_tool.py fuer die
        #     ausfuehrliche Begruendung (gleiches Muster ueberall).
        # EN: Also refresh the preview when switching tools, not just on
        #     selection change -- see rotate_tool.py for the full
        #     rationale (same pattern everywhere).
        super().showEvent(event)
        self._auswahl_geaendert()

    # -- Vorschau / Auswahl ---------------------------------------------------

    def _auswahl_geaendert(self) -> None:
        # DE: Ueberspringen, wenn nicht sichtbar -- siehe die ausfuehrliche
        #     Begruendung in rotate_tool.py's _auswahl_geaendert(). showEvent()
        #     holt die Vorschau nach, sobald das Werkzeug wieder sichtbar wird.
        # EN: Skip when not visible -- see the detailed rationale in
        #     rotate_tool.py's _auswahl_geaendert(). showEvent() catches the
        #     preview up once the tool becomes visible again.
        if not self.isVisible():
            return
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
        self._titel_feld.setText(wp.lesezeichen_titel)
        self._ebene_feld.setCurrentIndex(self._ebene_feld.findData(wp.lesezeichen_ebene))

    def _setzen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        self.liste.vor_aenderung_sichern()
        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        wp.lesezeichen_titel = self._titel_feld.text().strip()
        wp.lesezeichen_ebene = self._ebene_feld.currentData()
        self.liste.item_aktualisieren(item)
        self._uebersicht_aktualisieren()

        self._titel_feld.clear()
        naechste_zeile = self.liste.row(item) + 1
        if naechste_zeile < self.liste.count():
            self.liste.setCurrentRow(naechste_zeile)

    def _entfernen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        self.liste.vor_aenderung_sichern()
        wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
        wp.lesezeichen_titel = ""
        wp.lesezeichen_ebene = _KAPITEL
        self.liste.item_aktualisieren(item)
        self._titel_feld.clear()
        self._uebersicht_aktualisieren()

    # -- Uebersicht / overview --------------------------------------------

    def _uebersicht_aktualisieren(self) -> None:
        self._uebersicht.clear()
        for i in range(self.liste.count()):
            wp: WorkingPage = self.liste.item(i).data(Qt.ItemDataRole.UserRole)
            if not wp.lesezeichen_titel:
                continue
            einrueckung = "        " if wp.lesezeichen_ebene >= _UNTERKAPITEL else ""
            text = self.tr("Seite {0}: {1}{2}").format(i + 1, einrueckung, wp.lesezeichen_titel)
            eintrag = QListWidgetItem(text)
            eintrag.setData(Qt.ItemDataRole.UserRole, i)
            self._uebersicht.addItem(eintrag)

    def _zu_seite_springen(self, eintrag: QListWidgetItem) -> None:
        zeile = eintrag.data(Qt.ItemDataRole.UserRole)
        self.liste.setCurrentRow(zeile)
