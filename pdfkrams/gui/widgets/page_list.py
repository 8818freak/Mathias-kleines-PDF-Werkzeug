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
from typing import Callable

from PySide6.QtCore import QCoreApplication, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap, QTransform
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from pdfkrams.core.document import PageSource, WorkingPage, render_rgb

# DE: Kantenlaenge der Miniaturbilder in Pixeln.
# EN: Edge length of thumbnail images in pixels.
THUMB_GROESSE = 160

# DE: Wie viele Schritte Rueckgaengig/Wiederholen vorgehalten werden.
# EN: How many undo/redo steps are kept.
_VERLAUF_LIMIT = 50


def _basis_pixmap(source: PageSource, max_dim: int) -> QPixmap:
    """DE: Unveraendertes Vorschaubild einer Seite erzeugen.
    EN: Build the unmodified preview image of a page."""
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
    pixmap = _basis_pixmap(wp.source, max_dim)
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
    return pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)


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

    def seiten(self) -> list[WorkingPage]:
        """DE: Aktuelle Seitenreihenfolge als Liste liefern.
        EN: Return the current page ordering as a list."""
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]
