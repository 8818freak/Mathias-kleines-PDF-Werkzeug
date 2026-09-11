"""
DE: Werkzeug "Schwärzen": beliebig viele Bereiche einer Seite dauerhaft
    unkenntlich machen -- deckend schwarze Rechtecke, die beim Export
    wirklich in die Bildpixel eingebrannt werden (nicht nur optisch
    ueberdeckt), siehe core/schwaerzung.py fuer die technischen Details
    dazu. Rechtecke werden per Maus direkt in der Vorschau gezogen,
    verschoben und in der Groesse veraendert -- wie bei den anderen
    Werkzeugen mit guter Vergroesserung (Zoom/Verschieben). Ein
    "Übertragen"-Knopf kopiert die Rechtecke der aktuellen Seite auf
    weitere Seiten -- praktisch fuer wiederkehrende Angaben (z. B. eine
    Aktennummer oben auf jeder Seite).

EN: "Redact" tool: permanently obscure any number of areas on a page --
    fully opaque black rectangles that are actually burned into the image
    pixels on export (not just visually covered), see core/schwaerzung.py
    for the technical details. Rectangles are drawn, moved, and resized
    directly in the preview with the mouse -- with good zoom/pan like the
    other tools. A "Transfer" button copies the current page's rectangles
    onto further pages -- handy for recurring information (e.g. a case
    number at the top of every page).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget, vorschau_pixmap
from pdfkrams.gui.widgets.schwaerzung_canvas import SchwaerzungsCanvas

_VORSCHAU_GROESSE = 1000

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"


class SchwaerzungToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das dauerhafte Schwaerzen von Seitenbereichen.
    EN: GUI page for permanently redacting page areas.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())

        hinweis = QLabel(
            self.tr("Auf leerer Fläche ziehen zeichnet ein neues Rechteck; ein bestehendes anklicken "
                   "wählt es aus (Ziehen im Inneren verschiebt, an einer Ecke ändert die Größe). "
                   "Die Rechtecke werden beim Speichern dauerhaft in die Bildpixel eingebrannt -- "
                   "nicht nur optisch überdeckt. Betroffene Seiten werden dafür automatisch "
                   "gerastert, auch wenn sie sonst verlustfrei als Vektorseite exportiert würden.")
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
        btn_einpassen.clicked.connect(lambda: self._canvas.einpassen())
        zoom_zeile.addWidget(btn_zoom_aus)
        zoom_zeile.addWidget(self._zoom_label)
        zoom_zeile.addWidget(btn_zoom_ein)
        zoom_zeile.addWidget(btn_einpassen)
        zoom_zeile.addStretch(1)

        self._canvas = SchwaerzungsCanvas()
        self._canvas.schwaerzungenGeaendert.connect(self._canvas_geaendert)
        self._canvas.zoomGeaendert.connect(self._zoom_anzeige_aktualisieren)
        self._canvas.ziehenBegonnen.connect(self.liste.vor_aenderung_sichern)

        zeile = QHBoxLayout()
        btn_ausgewaehlte_loeschen = QPushButton(self.tr("Ausgewähltes Rechteck löschen"))
        btn_ausgewaehlte_loeschen.clicked.connect(self._ausgewaehlte_loeschen)
        btn_alle_loeschen = QPushButton(self.tr("Alle auf dieser Seite löschen"))
        btn_alle_loeschen.clicked.connect(self._alle_loeschen)
        zeile.addWidget(btn_ausgewaehlte_loeschen)
        zeile.addWidget(btn_alle_loeschen)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)

        gruppe = QGroupBox(self.tr("Rechtecke der aktuellen Seite übertragen auf:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)
        btn_uebertragen = QPushButton(self.tr("Übertragen"))
        btn_uebertragen.setToolTip(
            self.tr("Kopiert die Rechtecke der aktuellen Seite auf jede Seite im gewählten Bereich "
                   "-- praktisch für wiederkehrende Angaben (z. B. eine Aktennummer oben auf "
                   "jeder Seite).")
        )
        btn_uebertragen.clicked.connect(self._uebertragen)
        gruppe_layout.addWidget(btn_uebertragen)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addLayout(zoom_zeile)
        layout.addWidget(self._canvas, 1)
        layout.addLayout(zeile)
        layout.addWidget(gruppe)
        layout.addStretch(0)

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

    # -- Vorschau / preview -------------------------------------------------

    def _auswahl_geaendert(self) -> None:
        wp = self.liste.aktuelle_seite()
        if wp is None:
            self._canvas.seite_setzen(None, [])
            return
        pixmap = vorschau_pixmap(wp, _VORSCHAU_GROESSE)
        self._canvas.seite_setzen(pixmap, wp.schwaerzungen)

    def _zoom_anzeige_aktualisieren(self, zoom: float) -> None:
        self._zoom_label.setText(self.tr("{0} %").format(round(zoom * 100)))

    def _canvas_geaendert(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        wp = item.data(Qt.ItemDataRole.UserRole)
        wp.schwaerzungen = self._canvas.rechtecke()
        self.liste.item_aktualisieren(item)

    def _ausgewaehlte_loeschen(self) -> None:
        self.liste.vor_aenderung_sichern()
        if not self._canvas.entferne_ausgewaehlte():
            return
        self._canvas_geaendert()

    def _alle_loeschen(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        wp = item.data(Qt.ItemDataRole.UserRole)
        if not wp.schwaerzungen:
            return
        self.liste.vor_aenderung_sichern()
        self._canvas.alle_entfernen()
        self._canvas_geaendert()

    # -- Übertragen / transfer -----------------------------------------------

    def _uebertragen(self) -> None:
        quelle_item = self.liste.currentItem()
        if quelle_item is None:
            return
        quelle_wp = quelle_item.data(Qt.ItemDataRole.UserRole)
        if not quelle_wp.schwaerzungen:
            QMessageBox.information(
                self, self.tr("Keine Rechtecke"),
                self.tr("Die aktuelle Seite hat noch keine Schwärzungen zum Übertragen."),
            )
            return

        ziel = [item for item in self._ziel_elemente() if item is not quelle_item]
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Auswahl"), self.tr("Bitte zuerst Seiten in der Liste links auswählen.")
            )
            return

        anzeige = Fortschrittsanzeige(self, self.tr("Schwärzungen werden übertragen …"), len(ziel))
        try:
            with self.liste.stapelverarbeitung():
                for i, item in enumerate(ziel, start=1):
                    wp = item.data(Qt.ItemDataRole.UserRole)
                    wp.schwaerzungen = list(quelle_wp.schwaerzungen)
                    self.liste.item_aktualisieren(item)
                    anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()

        QMessageBox.information(
            self, self.tr("Fertig"), self.tr("Auf {0} Seite(n) übertragen.").format(len(ziel))
        )
