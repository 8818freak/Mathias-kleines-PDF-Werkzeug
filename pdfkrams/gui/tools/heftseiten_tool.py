"""
DE: Werkzeug "Heftseiten teilen": Doppelseiten-Scans eines Sattelhefts (je
    ein Scan zeigt zwei Buchseiten nebeneinander, in der physisch
    gestapelten Reihenfolge) in Einzelseiten teilen und automatisch in die
    richtige Lesereihenfolge bringen -- Portierung von cut_and_sort_scan.py,
    aber ohne externe Werkzeuge (kein ImageMagick) und mit der bestehenden
    Dreh-/Teilen-Logik der App.

    Normale (gleich breite) Scans werden automatisch mittig geteilt. Ist
    ein Scan deutlich breiter als die uebrigen -- typischerweise ein
    Umschlag, oft mit mehreren eigenen Seiten in einem Bild (Ruecktitel,
    Adressliste, Vortitel, Klappe, …) -- bekommt der Nutzer denselben
    Ziehen-Editor wie im Teilen-Werkzeug (inkl. Zoom) und legt die Schnitte
    selbst fest, beliebig viele. Die Sattelheft-Formel weiss bereits, auf
    welche zwei Seitenzahlen des fertigen Dokuments dieses eine Scan-Blatt
    gehoert -- der Nutzer muss im selben Dialog nur noch angeben, welche
    der geschnittenen Teile zu welcher der beiden Seiten gehoeren. Die
    Einsortierung selbst -- auch fuer die ueberbreiten Scans -- geschieht
    danach vollautomatisch ueber dieselbe Formel wie bei den normalen
    Scans, kein manuelles Ziehen in der Liste noetig.

EN: "Split booklet pages" tool: splits double-page spread scans of a
    saddle-stitched booklet (each scan shows two book pages side by side,
    in physically stacked order) into single pages and automatically puts
    them into the correct reading order -- a port of cut_and_sort_scan.py,
    but without external tools (no ImageMagick) and using the app's
    existing rotate/split logic.

    Normal (equally wide) scans are automatically split down the middle.
    If a scan is clearly wider than the others -- typically a cover, often
    containing several independent pages in one image (back title, address
    list, front title, flap, …) -- the user gets the same drag editor as in
    the split tool (including zoom) and sets the cuts themselves, as many
    as needed. The saddle-stitch formula already knows which two page
    numbers of the finished document this one scan sheet belongs to -- in
    the same dialog the user only needs to say which of the cut parts
    belong to which of the two pages. Placement itself -- including for
    the overwide scans -- then happens fully automatically via the same
    formula as for normal scans, no manual dragging in the list needed.
"""

from __future__ import annotations

import statistics
import uuid

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from pdfkrams.core import arbeitsordner
from pdfkrams.core.document import SplitSpec, WorkingPage
from pdfkrams.core.export_dateien import bild_materialisieren
from pdfkrams.core.heftseiten import lesereihenfolge
from pdfkrams.core.rotate import normalisiert, rotiertes_bild
from pdfkrams.core.split import teile_bild
from pdfkrams.gui.bildkonvertierung import pil_zu_qpixmap as _als_qpixmap
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.ueberbreite_dialog import ueberbreite_seite_teilen_abfragen

# DE: Ab welchem Vielfachen der ueblichen Breite ein Scan als "ueberbreit" gilt.
# EN: From what multiple of the usual width a scan counts as "overwide".
_UEBERBREITE_SCHWELLE = 1.3


class HeftseitenToolWidget(QWidget):
    """
    DE: GUI-Seite fuer das Teilen und Sortieren von Heft-Doppelseiten.
    EN: GUI page for splitting and sorting booklet double-page spreads.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        hinweis = QLabel(
            "In der Dateiliste links die Doppelseiten-Scans eines Hefts in "
            "ihrer physisch gestapelten Reihenfolge auswählen (mehrfach "
            "anklicken bzw. mit Cmd/Shift).\n\n"
            "Normale Scans werden automatisch mittig geteilt und beide "
            "Hälften in die Sattelheft-Lesereihenfolge gebracht: aus Scan "
            "1, 2, 3, … wird Seite 1, 2, 3, … in der richtigen Reihenfolge, "
            "so wie sie physisch im Heft liegen.\n\n"
            "Ist ein Scan deutlich breiter als die übrigen (Umschlag, "
            "Aufklappseite -- oft mit mehreren eigenen Seiten in einem "
            "Bild), öffnet sich der Ziehen-Editor aus „Seiten teilen“ "
            "(inkl. Zoom): dort selbst beliebig viele Schnitte festlegen "
            "und angeben, welche Teile zu welcher der beiden Zielseiten "
            "gehören -- die Einsortierung geschieht danach automatisch, "
            "kein manuelles Ziehen nötig."
        )
        hinweis.setWordWrap(True)

        self._dreh_feld = QCheckBox("Scans sind quer eingescannt -- abwechselnd um 90° drehen")
        self._dreh_feld.setToolTip(
            "Für Hefte, die als Doppelseite quer gescannt wurden: dreht jeden "
            "zweiten Scan um +90°, die dazwischenliegenden um -90°, bevor "
            "geteilt wird."
        )

        self._btn_verarbeiten = QPushButton("Ausgewählte Scans teilen + sortieren")
        self._btn_verarbeiten.clicked.connect(self._verarbeiten)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(self._dreh_feld)
        layout.addStretch(1)
        layout.addWidget(self._btn_verarbeiten)

    def _verarbeiten(self) -> None:
        items = sorted(self.liste.selectedItems(), key=self.liste.row)
        if not items:
            QMessageBox.information(
                self, "Keine Auswahl",
                "Bitte zuerst die Doppelseiten-Scans in der Liste auswählen.",
            )
            return

        abwechselnd = self._dreh_feld.isChecked()

        try:
            self._verarbeiten_inner(items, abwechselnd)
        except Abgebrochen:
            return

    def _verarbeiten_inner(self, items, abwechselnd: bool) -> None:
        # -- Phase 1: alle Bloecke rendern (gedreht) und Breiten messen --
        # DE: Liste statt Dict, da QListWidgetItem in PySide6 nicht hashbar ist.
        # EN: List instead of dict, since QListWidgetItem isn't hashable in PySide6.
        gerendert = []  # parallel zu items: (bild, dpi)
        anzeige = Fortschrittsanzeige(self, "Scans werden gerendert …", len(items))
        try:
            for idx, item in enumerate(items):
                wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
                zusatz = (270.0 if idx % 2 == 0 else 90.0) if abwechselnd else 0.0
                gedreht_winkel = normalisiert(wp.rotation + zusatz)
                gerendert.append(rotiertes_bild(wp.source, gedreht_winkel, wp.spiegel_h, wp.spiegel_v))
                anzeige.callback(idx + 1, len(items))
        finally:
            anzeige.schliessen()

        breiten = [bild.width for bild, _ in gerendert]
        referenzbreite = statistics.median(breiten)
        arbeits_unterordner = arbeitsordner.pfad() / uuid.uuid4().hex

        # DE: Volle Lesereihenfolge im Voraus berechnen -- daraus ergibt sich
        #     fuer jeden Block, auf welche Zielseite seine "west"- bzw.
        #     "ost"-Haelfte gehoert, auch fuer ueberbreite Bloecke mit mehr
        #     als zwei Teilen (die werden per Grenze auf genau diese beiden
        #     Zielseiten aufgeteilt).
        # EN: Compute the full reading order upfront -- this gives, for
        #     every block, which target page its "west" resp. "ost" half
        #     belongs to, even for overwide blocks with more than two parts
        #     (those get split across exactly these two target pages via
        #     the boundary).
        volle_reihenfolge = lesereihenfolge(len(items))
        ziel_seite = {paar: rang + 1 for rang, paar in enumerate(volle_reihenfolge)}

        # -- Phase 2a: ueberbreite Bloecke interaktiv abfragen (VOR der --
        #    Fortschrittsanzeige, sonst blockiert deren Fenster-Modalitaet
        #    Eingaben fuer den gleichzeitig geoeffneten Ueberbreite-Dialog,
        #    da beide dasselbe Elternfenster haben -- der Dialog erscheint
        #    dann zwar, laesst sich aber nicht bedienen).
        # EN: Phase 2a: interactively ask about overwide blocks BEFORE the
        #     progress dialog -- otherwise its window modality blocks input
        #     to the simultaneously open overwide dialog, since both share
        #     the same parent window (the dialog appears but can't be
        #     interacted with).
        ueberbreite_antworten = {}  # block_idx -> (positionen, grenze)
        for idx, (item, (bild, dpi)) in enumerate(zip(items, gerendert)):
            if bild.width > referenzbreite * _UEBERBREITE_SCHWELLE:
                wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
                vorschlag = max(2, round(bild.width / (referenzbreite / 2)))
                positionen, grenze = ueberbreite_seite_teilen_abfragen(
                    self, _als_qpixmap(bild), wp.source.path.name, vorschlag,
                    ziel_seite[(idx, "west")], ziel_seite[(idx, "ost")],
                )
                ueberbreite_antworten[idx] = (positionen, grenze)

        # -- Phase 2b: jeden Block teilen -- normal mittig, ueberbreit nach Vorgabe --
        slot_inhalt = {}  # (block_idx, "west"|"ost") -> Liste von PageSource

        anzeige = Fortschrittsanzeige(self, "Seiten werden geteilt …", len(items))
        try:
            for idx, (item, (bild, dpi)) in enumerate(zip(items, gerendert)):
                if idx not in ueberbreite_antworten:
                    west_bild, ost_bild = teile_bild(bild, SplitSpec(positionen_v=[0.5]))
                    slot_inhalt[(idx, "west")] = [
                        bild_materialisieren(west_bild, dpi, arbeits_unterordner, f"n{idx}_west")]
                    slot_inhalt[(idx, "ost")] = [
                        bild_materialisieren(ost_bild, dpi, arbeits_unterordner, f"n{idx}_ost")]
                else:
                    positionen, grenze = ueberbreite_antworten[idx]
                    wp: WorkingPage = item.data(Qt.ItemDataRole.UserRole)
                    teile = teile_bild(bild, SplitSpec(positionen_v=positionen))
                    quellen = [bild_materialisieren(teil, dpi, arbeits_unterordner, f"{wp.source.path.stem}_teil{i}")
                              for i, teil in enumerate(teile, start=1)]
                    slot_inhalt[(idx, "west")] = quellen[:grenze]
                    slot_inhalt[(idx, "ost")] = quellen[grenze:]
                anzeige.callback(idx + 1, len(items))
        finally:
            anzeige.schliessen()

        ueberbreite_anzahl = len(ueberbreite_antworten)

        # -- Phase 3: alles in der Sattelheft-Lesereihenfolge zusammensetzen --
        neue_quellen = [quelle for paar in volle_reihenfolge for quelle in slot_inhalt[paar]]
        self.liste.mehrere_ersetzen(items, neue_quellen)

        QMessageBox.information(
            self, "Fertig",
            f"{len(items)} Scans zu {len(neue_quellen)} Einzelseiten geteilt und einsortiert "
            f"({ueberbreite_anzahl} davon überbreit, individuell geteilt).",
        )
