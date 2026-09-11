"""
DE: Wiederverwendbare Miniaturansicht-Liste fuer Seiten. Zeigt eine Reihe
    von WorkingPage-Objekten als Vorschaubilder (unter Beruecksichtigung
    ihrer Drehung/Spiegelung), per Drag&Drop innerhalb der Liste neu
    anordbar. Wird von jedem Werkzeug verwendet, das mit einer geordneten
    Seitenliste arbeitet, damit dieses Verhalten nur einmal gebaut wird.

    Enthaelt auch die Rueckgaengig/Wiederholen-Verwaltung fuer die gesamte
    App: statt feingranularer Befehlsobjekte pro Werkzeug wird jeweils der
    komplette Listenzustand (Reihenfolge + eine Kopie jeder WorkingPage) vor
    einer Aenderung gesichert. Fuer eine Seitenliste dieser Groessenordnung
    ist das einfach und robust, ohne dass jedes Werkzeug eigene
    Undo-Befehle schreiben muss -- ein Werkzeug ruft lediglich
    `vor_aenderung_sichern()` auf, bevor es etwas veraendert.

EN: Reusable thumbnail list widget for pages. Displays a sequence of
    WorkingPage objects as preview images (respecting their rotation/mirror
    state), reorderable via drag&drop within the list. Used by every tool
    that works with an ordered page list, so this behaviour is built
    exactly once.

    Also holds the undo/redo management for the whole app: instead of
    fine-grained command objects per tool, the complete list state (order
    + a copy of every WorkingPage) is saved before a change. For a page
    list of this scale that's simple and robust, without every tool having
    to write its own undo commands -- a tool just calls
    `vor_aenderung_sichern()` before it changes anything.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QCoreApplication, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from pdfkrams.core.document import PageSource, WorkingPage, render_rgb
from pdfkrams.core.metadaten import dateiname_vorschlagen, leere_rohdaten, pdf_felder
from pdfkrams.einstellungen import einstellungen

# DE: Kantenlaenge der Miniaturbilder in Pixeln.
# EN: Edge length of thumbnail images in pixels.
THUMB_GROESSE = 160

# DE: Wie viele Schritte Rueckgaengig/Wiederholen vorgehalten werden.
# EN: How many undo/redo steps are kept.
_VERLAUF_LIMIT = 50


# DE: Cache-Groesse grosszuegig gewaehlt -- bei Dokumenten mit einigen
#     hundert Seiten (real vorkommend, siehe z. B. das 912-seitige
#     Testdokument) reicht ein kleiner Cache nicht, um wenigstens alle
#     Miniaturen gleichzeitig warm zu halten.
# EN: Cache size chosen generously -- for documents with a few hundred
#     pages (a real occurrence, see e.g. the 912-page test document), a
#     small cache isn't enough to keep even just all thumbnails warm at
#     the same time.
_BASIS_PIXMAP_CACHE_GROESSE = 1500


@lru_cache(maxsize=_BASIS_PIXMAP_CACHE_GROESSE)
def basis_pixmap(source: PageSource, max_dim: int) -> QPixmap:
    """DE: Unveraendertes Vorschaubild einer Seite erzeugen -- gecacht, da
        das Rendern aus der Quelldatei (PDF-Rasterung bzw. Bild-Dekodierung)
        der eigentlich teure Teil ist, nicht die anschliessende Drehung/
        Schwaerzung (die aendert sich haeufiger und bleibt daher bewusst
        UNgecacht, siehe vorschau_pixmap). `source` ist unveraenderlich
        (frozen dataclass) und referenziert nie eine nachtraeglich
        veraenderte Datei -- bearbeitete Seiten bekommen beim
        Materialisieren immer eine neue Datei mit neuem Pfad (siehe
        core/export_dateien.py's bild_materialisieren), nie denselben Pfad
        erneut. Der Cache kann also fuer die gesamte Programmlaufzeit
        gueltig bleiben.
    EN: Build the unmodified preview image of a page -- cached, since
        rendering from the source file (PDF rasterization resp. image
        decoding) is the actually expensive part, not the subsequent
        rotation/redaction (which changes more often and is therefore
        deliberately left UNcached, see vorschau_pixmap). `source` is
        immutable (frozen dataclass) and never references a file that
        gets modified afterward -- edited pages always get a new file
        with a new path when materialized (see core/export_dateien.py's
        bild_materialisieren), never the same path again. So the cache
        can stay valid for the entire program's runtime."""
    rgb_bytes, breite, hoehe = render_rgb(source, max_dim)
    bild = QImage(rgb_bytes, breite, hoehe, breite * 3, QImage.Format.Format_RGB888)
    # DE: Kopie noetig, da rgb_bytes nach Funktionsende freigegeben wird.
    # EN: Copy needed because rgb_bytes goes out of scope after this call.
    return QPixmap.fromImage(bild.copy())


def vorschau_pixmap(wp: WorkingPage, max_dim: int) -> QPixmap:
    """
    DE: Vorschaubild einer Arbeitsseite inkl. Drehung/Spiegelung erzeugen --
        also so, wie die Seite nach diesen beiden Bearbeitungen aussehen
        wird. Wird sowohl fuer die Listen-Miniaturen als auch fuer die
        grosse Vorschau anderer Werkzeuge (z. B. Seiten teilen) verwendet.

    EN: Build the preview image of a working page including rotation/mirror
        -- i.e. how the page will look after those two edits. Used both for
        the list thumbnails and for the large preview of other tools (e.g.
        Split Pages).
    """
    pixmap = basis_pixmap(wp.source, max_dim)
    if wp.rotation == 0.0 and not wp.spiegel_h and not wp.spiegel_v:
        return pixmap
    transform = QTransform()
    # DE: Reihenfolge passt zu core.rotate.bild_transformieren: erst spiegeln, dann drehen.
    # EN: Order matches core.rotate.bild_transformieren: mirror first, then rotate.
    if wp.spiegel_h:
        transform.scale(-1, 1)
    if wp.spiegel_v:
        transform.scale(1, -1)
    if wp.rotation:
        transform.rotate(wp.rotation)
    pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
    return _schwaerzungen_zeichnen(pixmap, wp.schwaerzungen)


def _schwaerzungen_zeichnen(pixmap: QPixmap, schwaerzungen: list[tuple[float, float, float, float]]) -> QPixmap:
    """DE: Schwaerzungs-Rechtecke deckend schwarz auf eine Kopie von
        `pixmap` zeichnen -- damit Miniaturen UND die Vorschau anderer
        Werkzeuge immer zeigen, was beim Export tatsaechlich unkenntlich
        gemacht wird (siehe core/schwaerzung.py fuer die eigentliche,
        dauerhafte Anwendung beim Export).
    EN: Draw redaction rectangles fully opaque black onto a copy of
        `pixmap` -- so thumbnails AND other tools' previews always show
        what actually gets redacted on export (see core/schwaerzung.py
        for the actual, permanent application on export)."""
    if not schwaerzungen:
        return pixmap
    ergebnis = QPixmap(pixmap)
    painter = QPainter(ergebnis)
    breite, hoehe = ergebnis.width(), ergebnis.height()
    farbe = QColor(einstellungen.schwaerzungsfarbe())
    for x0, y0, x1, y1 in schwaerzungen:
        painter.fillRect(QRectF(x0 * breite, y0 * hoehe, (x1 - x0) * breite, (y1 - y0) * hoehe), farbe)
    painter.end()
    return ergebnis


def _thumbnail(wp: WorkingPage) -> QPixmap:
    return vorschau_pixmap(wp, THUMB_GROESSE)


def _text(wp: WorkingPage) -> str:
    """DE: Anzeigetext mit Hinweis auf Drehung/Spiegelung/Teilung, falls vorhanden.
    EN: Display text noting rotation/mirror/split, if any."""
    # DE: pyside6-lupdate extrahiert hier NICHTS automatisch -- der String
    #     im translate()-Aufruf innerhalb der Lambda ist die Variable
    #     "text", kein literales Argument. Uebersetzungen fuer die unten
    #     per t(...) verwendeten Textfragmente muessen von Hand in die
    #     .ts-Datei eingetragen werden (Kontext "PageListWidget").
    # EN: pyside6-lupdate extracts NOTHING here automatically -- the
    #     string in the translate() call inside the lambda is the
    #     variable "text", not a literal argument. Translations for the
    #     text fragments used via t(...) below must be added to the .ts
    #     file by hand (context "PageListWidget").
    t = lambda text: QCoreApplication.translate("PageListWidget", text)  # noqa: E731
    zusatz = []
    if wp.rotation:
        zusatz.append(f"{wp.rotation:+.1f}°")
    if wp.spiegel_h:
        zusatz.append(t("horiz. gespiegelt"))
    if wp.spiegel_v:
        zusatz.append(t("vert. gespiegelt"))
    if wp.split:
        spalten = len(wp.split.positionen_v) + 1
        zeilen = len(wp.split.positionen_h) + 1
        if zeilen == 1:
            zusatz.append(t("{0} Teile (senkrecht)").format(spalten))
        elif spalten == 1:
            zusatz.append(t("{0} Teile (waagerecht)").format(zeilen))
        else:
            zusatz.append(t("{0}×{1} Raster").format(zeilen, spalten))
    if wp.ziel_nummer is not None:
        zusatz.append(t("→ Ziel {0}").format(wp.ziel_nummer))
    if wp.schwaerzungen:
        zusatz.append(
            t("1 Schwärzung") if len(wp.schwaerzungen) == 1
            else t("{0} Schwärzungen").format(len(wp.schwaerzungen))
        )
    if not zusatz:
        return wp.source.label
    return f"{wp.source.label} ({', '.join(zusatz)})"


class PageListWidget(QListWidget):
    """
    DE: Liste von Seiten mit Miniaturansicht, Mehrfachauswahl,
        Drag&Drop-Neuordnung innerhalb der Liste und Rueckgaengig/
        Wiederholen.

    EN: List of pages with thumbnail preview, multi-selection, drag&drop
        reordering within the list, and undo/redo.
    """

    # DE: Wird gesendet, wenn sich Inhalt oder Reihenfolge geaendert haben.
    # EN: Emitted whenever content or ordering has changed.
    geaendert = Signal()
    # DE: Wird gesendet, wenn sich verfuegbares Rueckgaengig/Wiederholen aendert.
    # EN: Emitted whenever available undo/redo changes.
    verlaufGeaendert = Signal()
    # DE: Wird gesendet, wenn ein Werkzeug die KOMPLETTE aktuelle Seitenliste
    #     erfolgreich als eine PDF-Datei exportiert hat (siehe
    #     gui/widgets/pdf_export.py) -- das Hauptfenster nutzt das, um
    #     diese Datei als neues Speicherziel fuer "Speichern" (Cmd+S) zu
    #     merken und die Markierung "ungespeicherte Aenderungen"
    #     zurueckzusetzen. Ohne das dachte das Hauptfenster nach einem
    #     Export ueber ein Werkzeug-eigenes "Als PDF exportieren" faelsch-
    #     licherweise weiterhin, es gaebe ungespeicherte Aenderungen, und
    #     Cmd+S schrieb nicht in die frisch exportierte Datei, sondern
    #     fragte wieder nach einem Speicherort.
    # EN: Emitted when a tool has successfully exported the ENTIRE current
    #     page list as one PDF file (see gui/widgets/pdf_export.py) -- the
    #     main window uses this to remember that file as the new save
    #     target for "Save" (Cmd+S) and to clear the "unsaved changes"
    #     flag. Without this, the main window kept incorrectly thinking
    #     there were unsaved changes after an export via a tool's own "Save
    #     as PDF" button, and Cmd+S asked for a save location again
    #     instead of writing into the freshly exported file.
    alsExportiertMarkiert = Signal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_GROESSE, THUMB_GROESSE))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setSpacing(8)
        self.setWordWrap(True)
        self.model().rowsMoved.connect(self._per_drag_verschoben)

        self._rueckgaengig_verlauf: list[list[WorkingPage]] = []
        self._wiederholen_verlauf: list[list[WorkingPage]] = []
        self._verlauf_gesperrt = False

        # DE: Dokumentweite PDF-Metadaten (Titel, Autor, Anbieter, ...) --
        #     anders als alles andere hier gilt das fuer das gesamte
        #     Dokument, nicht pro Seite, daher kein WorkingPage-Feld,
        #     sondern ein einzelnes geteiltes dict (siehe
        #     core/metadaten.py, gui/tools/metadaten_tool.py). Bewusst
        #     nicht im Rueckgaengig-Verlauf erfasst, wie die
        #     Einstellungen auch.
        # EN: Document-wide PDF metadata (title, author, provider, ...)
        #     -- unlike everything else here, this applies to the whole
        #     document, not per page, so it's not a WorkingPage field but
        #     a single shared dict (see core/metadaten.py,
        #     gui/tools/metadaten_tool.py). Deliberately not covered by
        #     undo/redo, same as Preferences.
        self.dokument_metadaten: dict[str, str] = leere_rohdaten()

    def _releasedatum_formatiert(self) -> str:
        wert = self.dokument_metadaten["releasedatum"]
        return einstellungen.datum_formatieren(date.fromisoformat(wert)) if wert else ""

    def pdf_metadaten_felder(self) -> dict[str, str]:
        """DE: Fasst die dokumentweiten Metadaten-Rohfelder (Titel, Autor,
            Anbieter, ...) zu den vier PDF-Standardfeldern zusammen --
            siehe core/metadaten.py's pdf_felder().
        EN: Merges the document-wide raw metadata fields (title, author,
            provider, ...) into the four standard PDF fields -- see
            core/metadaten.py's pdf_felder()."""
        return pdf_felder(self.dokument_metadaten, self._releasedatum_formatiert())

    def dateiname_vorschlag(self) -> str:
        """DE: Dateinamensvorschlag aus den Metadaten-Rohfeldern -- siehe
            core/metadaten.py's dateiname_vorschlagen().
        EN: Filename suggestion from the raw metadata fields -- see
            core/metadaten.py's dateiname_vorschlagen()."""
        return dateiname_vorschlagen(self.dokument_metadaten, self._releasedatum_formatiert())

    def _per_drag_verschoben(self, *_args) -> None:
        # DE: Drag&Drop-Umsortierung in der Liste selbst ist ebenfalls eine
        #     Aenderung, die rueckgaengig gemacht werden koennen soll --
        #     die Sicherung muss aber VOR der Verschiebung passiert sein,
        #     was rowsMoved (danach ausgeloest) nicht mehr leisten kann.
        #     Deshalb wird hier nur "geaendert" gemeldet; die Sicherung
        #     selbst passiert in startDrag().
        # EN: Drag&drop reordering within the list is also a change that
        #     should be undoable -- but the snapshot must happen BEFORE
        #     the move, which rowsMoved (fired afterwards) can no longer
        #     provide. So this only emits "changed" here; the actual
        #     snapshot happens in startDrag().
        self.geaendert.emit()

    def startDrag(self, supportedActions) -> None:  # noqa: N802 (Qt-Ueberschreibung)
        self.vor_aenderung_sichern()
        super().startDrag(supportedActions)

    # -- Rueckgaengig / Wiederholen ------------------------------------

    @staticmethod
    def _schnappschuss(seiten: list[WorkingPage]) -> list[WorkingPage]:
        return [copy.copy(wp) for wp in seiten]

    def vor_aenderung_sichern(self) -> None:
        """DE: Vor einer Aenderung aufrufen, um den aktuellen Zustand fuer
        Rueckgaengig zu sichern. Loescht den Wiederholen-Verlauf, wie bei
        jedem gewoehnlichen Undo/Redo-System. Waehrend einer
        `stapelverarbeitung()` ein No-Op, damit mehrere strukturelle
        Aenderungen als EIN Rueckgaengig-Schritt zaehlen.
        EN: Call before making a change, to save the current state for
        undo. Clears the redo history, as usual for undo/redo systems. A
        no-op during a `stapelverarbeitung()`, so several structural
        changes count as ONE undo step."""
        if self._verlauf_gesperrt:
            return
        self._rueckgaengig_verlauf.append(self._schnappschuss(self.seiten()))
        if len(self._rueckgaengig_verlauf) > _VERLAUF_LIMIT:
            self._rueckgaengig_verlauf.pop(0)
        self._wiederholen_verlauf.clear()
        self.verlaufGeaendert.emit()

    @contextmanager
    def stapelverarbeitung(self):
        """DE: Mehrere strukturelle Aenderungen (z. B. mehrere `ersetzen()`-
        Aufrufe in einer Schleife) als EINEN Rueckgaengig-Schritt buendeln.
        EN: Bundle several structural changes (e.g. several `ersetzen()`
        calls in a loop) into ONE undo step."""
        self.vor_aenderung_sichern()
        self._verlauf_gesperrt = True
        try:
            yield
        finally:
            self._verlauf_gesperrt = False

    def kann_rueckgaengig(self) -> bool:
        return bool(self._rueckgaengig_verlauf)

    def kann_wiederholen(self) -> bool:
        return bool(self._wiederholen_verlauf)

    def rueckgaengig(self) -> None:
        if not self._rueckgaengig_verlauf:
            return
        self._wiederholen_verlauf.append(self._schnappschuss(self.seiten()))
        self._zustand_setzen(self._rueckgaengig_verlauf.pop())
        self.verlaufGeaendert.emit()

    def wiederholen(self) -> None:
        if not self._wiederholen_verlauf:
            return
        self._rueckgaengig_verlauf.append(self._schnappschuss(self.seiten()))
        self._zustand_setzen(self._wiederholen_verlauf.pop())
        self.verlaufGeaendert.emit()

    def _zustand_setzen(self, seiten: list[WorkingPage]) -> None:
        """DE: Liste komplett aus einem gesicherten Zustand wiederherstellen.
        EN: Fully rebuild the list from a saved state."""
        self.clear()
        for wp in seiten:
            item = QListWidgetItem(QIcon(_thumbnail(wp)), _text(wp))
            item.setData(Qt.ItemDataRole.UserRole, wp)
            self.addItem(item)
        self.geaendert.emit()

    # -- Inhalt aendern / changing content ---------------------------------

    @staticmethod
    def _erzeuge_item(source: PageSource) -> QListWidgetItem:
        wp = WorkingPage(source=source)
        item = QListWidgetItem(QIcon(_thumbnail(wp)), _text(wp))
        item.setData(Qt.ItemDataRole.UserRole, wp)
        return item

    def seiten_anhaengen(
        self, sources: list[PageSource],
        fortschritt: Callable[[int, int], None] | None = None,
    ) -> None:
        """DE: Seiten am Ende der Liste einfuegen und Miniaturen rendern.
            `fortschritt`, falls angegeben, wird nach jeder gerenderten
            Miniatur mit (erledigt, gesamt) aufgerufen -- das Rendern
            einer Miniatur pro Seite ist der eigentlich langsame Teil
            beim Laden vielseitiger Dateien.
        EN: Append pages at the end of the list and render their
            thumbnails. `fortschritt`, if given, is called with (done,
            total) after each rendered thumbnail -- rendering one
            thumbnail per page is the actually slow part when loading
            many-page files."""
        self.vor_aenderung_sichern()
        for i, source in enumerate(sources, start=1):
            self.addItem(self._erzeuge_item(source))
            if fortschritt is not None:
                fortschritt(i, len(sources))
        self.geaendert.emit()

    def seiten_einfuegen(
        self, sources: list[PageSource], index: int,
        fortschritt: Callable[[int, int], None] | None = None,
    ) -> None:
        """DE: Seiten an einer bestimmten Stelle einfuegen (statt am Ende
            anzuhaengen, siehe seiten_anhaengen) -- fuer per Drag&Drop an
            eine konkrete Position in der bereits geoeffneten Liste
            gezogene Dateien.
        EN: Insert pages at a specific position (instead of appending at
            the end, see seiten_anhaengen) -- for files dragged & dropped
            at a specific position within the already-open list."""
        self.vor_aenderung_sichern()
        for i, source in enumerate(sources):
            self.insertItem(index + i, self._erzeuge_item(source))
            if fortschritt is not None:
                fortschritt(i + 1, len(sources))
        self.geaendert.emit()

    def ersetzen(self, item: QListWidgetItem, sources: list[PageSource]) -> None:
        """DE: Einen Eintrag durch eine oder mehrere neue Seiten an derselben
        Stelle ersetzen -- z. B. um eine konfigurierte Teilung tatsaechlich
        auszufuehren und die Teile als eigene, weiter bearbeitbare Seiten
        in die Liste einzusetzen.
        EN: Replace one entry with one or more new pages at the same spot
        -- e.g. to actually carry out a configured split and insert the
        parts as independent, further-editable pages into the list."""
        self.mehrere_ersetzen([item], sources)

    def mehrere_ersetzen(self, items: list[QListWidgetItem], sources: list[PageSource]) -> None:
        """DE: Mehrere (typischerweise aufeinanderfolgende) Eintraege durch
        eine neue Sequenz ersetzen, eingefuegt an der Stelle des ersten
        entfernten Eintrags -- z. B. um mehrere ausgewaehlte Doppelseiten-
        Scans durch ihre bereits geteilten und in Lesereihenfolge
        sortierten Einzelseiten zu ersetzen (Heftseiten-Werkzeug).
        EN: Replace several (typically consecutive) entries with a new
        sequence, inserted at the position of the first removed entry --
        e.g. to replace several selected double-page spread scans with
        their already split and reading-order-sorted single pages
        (booklet tool)."""
        if not items:
            return
        self.vor_aenderung_sichern()
        zeilen = sorted(self.row(it) for it in items)
        einfuegeposition = zeilen[0]
        for zeile in reversed(zeilen):
            self.takeItem(zeile)
        for versatz, source in enumerate(sources):
            self.insertItem(einfuegeposition + versatz, self._erzeuge_item(source))
        self.geaendert.emit()

    def neu_anordnen(self, neue_reihenfolge: list[QListWidgetItem]) -> None:
        """DE: Alle vorhandenen Eintraege (dieselben Objekte, keine neuen
        WorkingPages) in eine neue Reihenfolge bringen -- z. B. um eine
        durcheinandergeratene Seitenfolge nach zugewiesenen Zielnummern neu
        zu sortieren, ohne Drehung/Spiegelung/Teilung der einzelnen Seiten
        zu verlieren. `neue_reihenfolge` muss genau die aktuellen Eintraege
        enthalten, nur in der gewuenschten Reihenfolge.
        EN: Rearrange all existing entries (the same objects, no new
        WorkingPages) into a new order -- e.g. to re-sort a scrambled page
        sequence by assigned target numbers, without losing each page's
        rotation/mirror/split. `neue_reihenfolge` must contain exactly the
        current entries, just in the desired order."""
        self.vor_aenderung_sichern()
        for zeile in reversed(range(self.count())):
            self.takeItem(zeile)
        for item in neue_reihenfolge:
            self.addItem(item)
        self.geaendert.emit()

    def item_aktualisieren(self, item: QListWidgetItem) -> None:
        """DE: Miniaturbild und Text eines Eintrags neu erzeugen, z. B.
        nachdem seine WorkingPage veraendert wurde (Drehung/Spiegelung).
        Sichert selbst NICHT den Rueckgaengig-Zustand -- das muss der
        Aufrufer VOR der eigentlichen Aenderung per
        `vor_aenderung_sichern()` erledigen, da diese Methode oft nach
        mehreren Einzeleingaben (z. B. waehrend eines Maus-Drags) gerufen wird.
        EN: Regenerate an entry's thumbnail and text, e.g. after its
        WorkingPage was changed (rotation/mirror). Does NOT itself save
        undo state -- the caller must do that BEFORE the actual change via
        `vor_aenderung_sichern()`, since this method is often called after
        several individual inputs (e.g. during a mouse drag)."""
        wp = item.data(Qt.ItemDataRole.UserRole)
        item.setIcon(QIcon(_thumbnail(wp)))
        item.setText(_text(wp))

    def aktuelle_seite(self) -> WorkingPage | None:
        """DE: WorkingPage des fokussierten Eintrags liefern, falls vorhanden.
        EN: Return the WorkingPage of the focused entry, if any."""
        item = self.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def ausgewaehlte_entfernen(self) -> None:
        """DE: Markierte Eintraege aus der Liste loeschen.
        EN: Remove the currently selected entries from the list."""
        if not self.selectedItems():
            return
        self.vor_aenderung_sichern()
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self.geaendert.emit()

    def alle_entfernen(self) -> None:
        """DE: Gesamte Liste leeren. EN: Clear the entire list."""
        if self.count() == 0:
            return
        self.vor_aenderung_sichern()
        self.clear()
        self.geaendert.emit()

    def dokument_schliessen(self) -> None:
        """
        DE: Wie alle_entfernen(), zusaetzlich aber auch der Rueckgaengig-
            Verlauf und die dokumentweiten Metadaten (Titel, Autor, ...)
            werden zurueckgesetzt -- fuer "Datei schliessen", wo ein
            wirklich frischer Start gewuenscht ist (sonst koennte "Rueck-
            gaengig" die alte Datei zurueckholen, oder ihr Titel/Autor in
            das naechste, eigentlich neue Dokument durchsickern).
        EN: Like alle_entfernen(), but also resets the undo/redo history
            and the document-wide metadata (title, author, ...) -- for
            "Close file", where a genuinely fresh start is wanted
            (otherwise "Undo" could bring the old file back, or its
            title/author could leak into the next, supposedly new
            document).
        """
        self.clear()
        self._rueckgaengig_verlauf.clear()
        self._wiederholen_verlauf.clear()
        self.dokument_metadaten = leere_rohdaten()
        self.geaendert.emit()
        self.verlaufGeaendert.emit()

    def seiten(self) -> list[WorkingPage]:
        """DE: Aktuelle Seitenreihenfolge als Liste liefern.
        EN: Return the current page ordering as a list."""
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]
