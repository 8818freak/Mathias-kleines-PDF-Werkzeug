"""
DE: Werkzeug "Seiten drehen": Seiten per Maus-Drag frei geradeziehen, dazu
    Schnellaktionen fuer 90°/180°-Drehung und Spiegeln, jeweils wahlweise auf
    die aktuelle Seite, eine Auswahl oder alle Seiten angewendet. Fuer
    umgedreht eingescannte Doppelseiten gibt es eine Funktion, die
    abwechselnde Seiten in entgegengesetzte Richtungen dreht.

EN: "Rotate pages" tool: freely straighten pages via mouse drag, plus quick
    actions for 90°/180° rotation and mirroring, each applicable to the
    current page, a selection, or all pages. For alternately-scanned
    double-page spreads there's a function that rotates alternating pages
    in opposite directions.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.combine import export_pdf
from pdfkrams.core.rotate import normalisiert, rotiertes_bild, schraeglagen_korrektur_erkennen
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget, basis_pixmap
from pdfkrams.gui.widgets.rotate_canvas import RotateCanvas

# DE: Groesse, in der die aktuelle Seite in der grossen Vorschau gerendert wird.
# EN: Size at which the current page is rendered in the large preview.
_VORSCHAU_GROESSE = 1000

_AKTUELLE_SEITE = "Aktuelle Seite"
_AUSGEWAEHLTE_SEITEN = "Ausgewählte Seiten"
_ALLE_SEITEN = "Alle Seiten"


class RotateToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Geraderichten, Drehen und Spiegeln von Seiten.
        Arbeitet auf der von aussen uebergebenen, gemeinsamen Seitenliste.
    EN: GUI page for straightening, rotating, and mirroring pages. Works on
        the shared page list passed in from outside.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste
        # DE: Verhindert Rueckkopplungsschleifen beim Synchronisieren von
        #     Canvas und Zahlenfeld waehrend des Ladens einer Seite.
        # EN: Prevents feedback loops when syncing canvas and spinbox
        #     while loading a page.
        self._synchronisiere = False

        self.liste.itemSelectionChanged.connect(self._auswahl_geaendert)
        self.liste.currentItemChanged.connect(lambda *_: self._auswahl_geaendert())

        # -- Vorschau + Aktionen / preview + actions --------------------
        self._canvas = RotateCanvas()
        self._canvas.winkelGeaendert.connect(self._winkel_von_canvas)
        self._canvas.aenderungBegonnen.connect(self.liste.vor_aenderung_sichern)

        self._winkel_feld = QDoubleSpinBox()
        self._winkel_feld.setRange(-180.0, 180.0)
        self._winkel_feld.setDecimals(1)
        self._winkel_feld.setSuffix(" °")
        self._winkel_feld.setSingleStep(0.5)
        self._winkel_feld.valueChanged.connect(self._winkel_vom_feld)

        hinweis = QLabel(
            self.tr("Mit der Maus in der Vorschau ziehen, um die Seite geradezurichten "
                   "(die roten Linien helfen als Wasserwaage). Pfeiltasten für "
                   "Feinjustierung, Umschalt+Pfeil für größere Schritte.")
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
        self._canvas.zoomGeaendert.connect(self._zoom_anzeige_aktualisieren)

        self._geltungsbereich = QComboBox()
        self._geltungsbereich.addItem(self.tr(_AKTUELLE_SEITE), _AKTUELLE_SEITE)
        self._geltungsbereich.addItem(self.tr(_AUSGEWAEHLTE_SEITEN), _AUSGEWAEHLTE_SEITEN)
        self._geltungsbereich.addItem(self.tr(_ALLE_SEITEN), _ALLE_SEITEN)

        gruppe = QGroupBox(self.tr("Schnellaktionen – anwenden auf:"))
        gruppe_layout = QVBoxLayout(gruppe)
        gruppe_layout.addWidget(self._geltungsbereich)

        drehen_zeile = QHBoxLayout()
        for text, delta, taste in (
            (self.tr("↺ 90°"), -90.0, "Ctrl+L"),
            (self.tr("↻ 90°"), 90.0, "Ctrl+R"),
            (self.tr("180°"), 180.0, None),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _checked=False, d=delta: self._schnelldrehung(d))
            if taste is not None:
                # DE: "Ctrl" wird von Qt auf macOS automatisch zu Cmd --
                #     dieselbe Konvention wie bei den Standard-Kuerzeln
                #     (z. B. QKeySequence.StandardKey.Save).
                # EN: Qt automatically maps "Ctrl" to Cmd on macOS -- the
                #     same convention as the standard shortcuts (e.g.
                #     QKeySequence.StandardKey.Save).
                btn.setShortcut(QKeySequence(taste))
                btn.setShortcutEnabled(True)
            drehen_zeile.addWidget(btn)
        gruppe_layout.addLayout(drehen_zeile)

        spiegeln_zeile = QHBoxLayout()
        btn_spiegel_h = QPushButton(self.tr("Horizontal spiegeln"))
        btn_spiegel_h.clicked.connect(lambda: self._spiegeln("h"))
        btn_spiegel_v = QPushButton(self.tr("Vertikal spiegeln"))
        btn_spiegel_v.clicked.connect(lambda: self._spiegeln("v"))
        spiegeln_zeile.addWidget(btn_spiegel_h)
        spiegeln_zeile.addWidget(btn_spiegel_v)
        gruppe_layout.addLayout(spiegeln_zeile)

        weitere_zeile = QHBoxLayout()
        btn_zuruecksetzen = QPushButton(self.tr("Zurücksetzen"))
        btn_zuruecksetzen.setToolTip(self.tr("Drehung auf 0° und Spiegelung aus, für den gewählten Bereich."))
        btn_zuruecksetzen.clicked.connect(self._zuruecksetzen)
        btn_uebertragen = QPushButton(self.tr("Feinwinkel übertragen"))
        btn_uebertragen.setToolTip(
            self.tr("Den in der Vorschau eingestellten Winkel der aktuellen Seite auf den "
                   "gewählten Bereich übertragen.")
        )
        btn_uebertragen.clicked.connect(self._feinwinkel_uebertragen)
        weitere_zeile.addWidget(btn_zuruecksetzen)
        weitere_zeile.addWidget(btn_uebertragen)
        gruppe_layout.addLayout(weitere_zeile)

        btn_auto_erkennen = QPushButton(self.tr("Schräglage automatisch erkennen"))
        btn_auto_erkennen.setToolTip(
            self.tr("Schlägt für den gewählten Bereich je Seite einen Geraderichtungs-Winkel "
                   "vor, anhand der Textzeilen im Bild -- funktioniert nur bei Seiten mit "
                   "erkennbarem Zeilenmuster (nicht bei Fotos o. ä.), die dann unverändert "
                   "bleiben. Vorschlag wird direkt übernommen, aber wie gewohnt noch von "
                   "Hand nachjustierbar.")
        )
        btn_auto_erkennen.clicked.connect(self._winkel_automatisch_erkennen)
        gruppe_layout.addWidget(btn_auto_erkennen)

        btn_abwechselnd = QPushButton(self.tr("Abwechselnd 90° drehen (gerade/ungerade entgegengesetzt)"))
        btn_abwechselnd.setToolTip(
            self.tr("Für Hefte, die als Doppelseiten quer gescannt wurden: dreht jede "
                   "zweite Seite um +90°, die dazwischenliegenden um -90°.")
        )
        btn_abwechselnd.clicked.connect(self._abwechselnd_drehen)
        gruppe_layout.addWidget(btn_abwechselnd)

        self._btn_export = QPushButton(self.tr("Als PDF exportieren …"))
        self._btn_export.clicked.connect(self._exportieren)
        self._btn_export.setEnabled(self.liste.count() > 0)
        self.liste.geaendert.connect(
            lambda: self._btn_export.setEnabled(self.liste.count() > 0)
        )

        aussen = QVBoxLayout(self)
        aussen.addWidget(hinweis)
        aussen.addLayout(zoom_zeile)
        aussen.addWidget(self._canvas, 1)
        aussen.addWidget(self._winkel_feld)
        aussen.addWidget(gruppe)
        aussen.addStretch(0)
        aussen.addWidget(self._btn_export)

        self._steuerung_aktivieren(self.liste.aktuelle_seite() is not None)
        self._auswahl_geaendert()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        # DE: Wird auch beim Wechsel zu diesem Werkzeug ueber die
        #     Seitenleiste ausgeloest (QStackedWidget zeigt/versteckt
        #     Seiten per show()/hide()) -- ohne das wuerde die Vorschau
        #     hier stehen bleiben, wenn sich die Seite in einem ANDEREN
        #     Werkzeug geaendert hat, waehrend dieses im Hintergrund war
        #     (die Auswahl in der Liste aendert sich dabei ja nicht, nur
        #     der Inhalt der Seite selbst).
        # EN: Also fires when switching to this tool via the sidebar
        #     (QStackedWidget shows/hides pages via show()/hide()) --
        #     without this, the preview here would stay stale if the page
        #     changed in a DIFFERENT tool while this one was in the
        #     background (the list selection itself doesn't change, only
        #     the page's own content).
        super().showEvent(event)
        self._auswahl_geaendert()

    # -- Geltungsbereich / scope resolution --------------------------------

    def _ziel_elemente(self) -> list[QListWidgetItem]:
        """DE: Listeneintraege liefern, auf die Schnellaktionen wirken sollen.
        EN: Return the list entries that quick actions should act on."""
        modus = self._geltungsbereich.currentData()
        if modus == _ALLE_SEITEN:
            return [self.liste.item(i) for i in range(self.liste.count())]
        if modus == _AUSGEWAEHLTE_SEITEN:
            gewaehlt = self.liste.selectedItems()
            if gewaehlt:
                return gewaehlt
        aktuell = self.liste.currentItem()
        return [aktuell] if aktuell else []

    # -- Auswahl / Vorschau laden --------------------------------------

    def _auswahl_geaendert(self) -> None:
        wp = self.liste.aktuelle_seite()
        self._steuerung_aktivieren(wp is not None)
        if wp is None:
            self._canvas.seite_setzen(None, 0.0, False, False)
            return
        # DE: Bewusst basis_pixmap (ungedreht, gecacht) statt vorschau_pixmap
        #     -- die Canvas dreht/spiegelt selbst per painter.rotate(),
        #     braucht also das UNveraenderte Bild.
        # EN: Deliberately basis_pixmap (unrotated, cached) instead of
        #     vorschau_pixmap -- the canvas rotates/mirrors itself via
        #     painter.rotate(), so it needs the UNmodified image.
        pixmap = basis_pixmap(wp.source, _VORSCHAU_GROESSE)

        self._synchronisiere = True
        self._canvas.seite_setzen(pixmap, wp.rotation, wp.spiegel_h, wp.spiegel_v)
        self._winkel_feld.setValue(wp.rotation)
        self._synchronisiere = False

    def _zoom_anzeige_aktualisieren(self, zoom: float) -> None:
        self._zoom_label.setText(self.tr("{0} %").format(round(zoom * 100)))

    def _steuerung_aktivieren(self, an: bool) -> None:
        self._canvas.setEnabled(an)
        self._winkel_feld.setEnabled(an)

    # -- Live-Winkel der aktuellen Seite / live angle of the current page --

    def _winkel_von_canvas(self, winkel: float) -> None:
        if self._synchronisiere:
            return
        self._synchronisiere = True
        self._winkel_feld.setValue(winkel)
        self._synchronisiere = False
        self._aktuelle_seite_winkel_setzen(winkel)

    def _winkel_vom_feld(self, winkel: float) -> None:
        if self._synchronisiere:
            return
        self._synchronisiere = True
        self._canvas.winkel_setzen(winkel)
        self._synchronisiere = False
        self._aktuelle_seite_winkel_setzen(winkel)

    def _aktuelle_seite_winkel_setzen(self, winkel: float) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        wp = item.data(Qt.ItemDataRole.UserRole)
        wp.rotation = normalisiert(winkel)
        self.liste.item_aktualisieren(item)

    # -- Schnellaktionen / quick actions ------------------------------------

    def _schnelldrehung(self, delta_grad: float) -> None:
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            wp.rotation = normalisiert(wp.rotation + delta_grad)
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _spiegeln(self, achse: str) -> None:
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            if achse == "h":
                wp.spiegel_h = not wp.spiegel_h
            else:
                wp.spiegel_v = not wp.spiegel_v
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _zuruecksetzen(self) -> None:
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            wp.rotation = 0.0
            wp.spiegel_h = False
            wp.spiegel_v = False
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _feinwinkel_uebertragen(self) -> None:
        quelle = self.liste.currentItem()
        if quelle is None:
            return
        winkel = quelle.data(Qt.ItemDataRole.UserRole).rotation
        self.liste.vor_aenderung_sichern()
        for item in self._ziel_elemente():
            wp = item.data(Qt.ItemDataRole.UserRole)
            wp.rotation = winkel
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    def _winkel_automatisch_erkennen(self) -> None:
        """DE: Schlaegt fuer jede Seite im gewaehlten Bereich per
            Projektionsprofil-Analyse einen Geraderichtungswinkel vor und
            setzt ihn direkt (wie bei einer manuellen Eingabe -- weiter per
            Ziehen/Zahlenfeld korrigierbar). Seiten ohne zuverlaessig
            erkennbares Zeilenmuster (Fotos, grafiklastige Seiten) bleiben
            unveraendert; am Ende wird gemeldet, fuer wie viele das der
            Fall war.
        EN: Suggests a straightening angle for every page in the selected
            scope via projection-profile analysis and sets it directly
            (like a manual entry -- still adjustable afterwards via
            dragging/the number field). Pages without a reliably detectable
            line pattern (photos, graphics-heavy pages) are left unchanged;
            at the end, it's reported for how many that was the case."""
        ziel = self._ziel_elemente()
        if not ziel:
            QMessageBox.information(
                self, self.tr("Keine Auswahl"), self.tr("Bitte zuerst Seiten in der Liste links auswählen.")
            )
            return
        self.liste.vor_aenderung_sichern()
        unsicher = []
        anzeige = Fortschrittsanzeige(self, self.tr("Schräglage wird erkannt …"), len(ziel))
        try:
            for i, item in enumerate(ziel, start=1):
                wp = item.data(Qt.ItemDataRole.UserRole)
                bild, _dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
                korrektur = schraeglagen_korrektur_erkennen(bild)
                if korrektur is None:
                    unsicher.append(wp.source.path.name)
                else:
                    wp.rotation = normalisiert(wp.rotation + korrektur)
                    self.liste.item_aktualisieren(item)
                anzeige.callback(i, len(ziel))
        except Abgebrochen:
            return
        finally:
            anzeige.schliessen()
        self._auswahl_geaendert()
        if unsicher:
            QMessageBox.information(
                self, self.tr("Teilweise kein Vorschlag"),
                self.tr("Für {0} von {1} Seite(n) wurde keine zuverlässige Schräglage erkannt "
                       "(unverändert gelassen):\n{2}").format(
                    len(unsicher), len(ziel), "\n".join(unsicher[:10])
                ),
            )

    def _abwechselnd_drehen(self) -> None:
        elemente = self._ziel_elemente()
        if len(elemente) < 2:
            QMessageBox.information(
                self, self.tr("Zu wenige Seiten"),
                self.tr("Dafür müssen mindestens zwei Seiten im gewählten Bereich liegen."),
            )
            return
        self.liste.vor_aenderung_sichern()
        for i, item in enumerate(elemente):
            wp = item.data(Qt.ItemDataRole.UserRole)
            delta = 90.0 if i % 2 == 0 else -90.0
            wp.rotation = normalisiert(wp.rotation + delta)
            self.liste.item_aktualisieren(item)
        self._auswahl_geaendert()

    # -- Export -------------------------------------------------------------

    def _exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, self.tr("PDF speichern unter"), self.tr("gedreht.pdf"), self.tr("PDF-Datei (*.pdf)")
        )
        if not ziel:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, self.tr("PDF wird erstellt …"), len(seiten))
        try:
            export_pdf(seiten, Path(ziel), fortschritt=anzeige.callback)
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Export fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(self, self.tr("Fertig"), self.tr("PDF gespeichert unter:\n{0}").format(ziel))
