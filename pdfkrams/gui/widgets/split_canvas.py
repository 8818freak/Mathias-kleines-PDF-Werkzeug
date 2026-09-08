"""
DE: Interaktive Vorschauflaeche fuer das Teilen-Werkzeug. Zeigt eine Seite
    (bereits inkl. ihrer Drehung/Spiegelung) gross an, mit den geplanten
    Schnittlinien darueber -- senkrechte und waagerechte gleichzeitig, fuer
    ein echtes Zeilen-x-Spalten-Raster. Jede Linie laesst sich einzeln per
    Maus-Drag entlang ihrer Achse verschieben, begrenzt durch ihre
    Nachbarlinien; beim Ueberfahren einer Linie wechselt der Mauszeiger als
    Hinweis, dass sie sich greifen laesst.

    Zusaetzlich laesst sich die Ansicht vergroessern (Strg/Cmd+Scrollen bzw.
    Pinch-Geste am Trackpad, verankert am Mauszeiger) und verschieben
    (einfaches Scrollen/Wischen) -- wichtig, wenn viele schmale Spalten dicht
    beieinander liegen und ein Klick in der eingepassten Ansicht kaum
    treffgenau genug waere.

EN: Interactive preview area for the split tool. Displays a page (already
    including its rotation/mirror) at large size, with the planned cut
    lines overlaid -- vertical and horizontal at the same time, for a true
    row-by-column grid. Each line can be dragged individually along its
    axis, constrained by its neighboring lines; hovering over a line
    changes the cursor as a hint that it can be grabbed.

    The view can also be zoomed (Ctrl/Cmd+scroll or trackpad pinch, anchored
    at the cursor) and panned (plain scroll/swipe) -- important when many
    narrow columns sit close together and a click in the fitted view
    couldn't be precise enough.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

# DE: Abstand in Pixeln, innerhalb dessen ein Klick eine Linie trifft.
# EN: Distance in pixels within which a click hits a line.
_TREFFER_ABSTAND = 12.0
# DE: Mindestabstand zwischen zwei Linien bzw. zum Rand, als Anteil (0..1).
# EN: Minimum spacing between two lines resp. to the edge, as a fraction (0..1).
_MINDESTABSTAND = 0.01
# DE: Erlaubter Zoombereich. EN: Allowed zoom range.
_ZOOM_MIN = 1.0
_ZOOM_MAX = 40.0


class SplitCanvas(QWidget):
    """
    DE: Zeigt eine Seite mit ueberlagerten, verschiebbaren Schnittlinien
        (senkrecht und waagerecht gleichzeitig), zoom- und verschiebbar.
        `linienGeaendert` feuert mit (positionen_v, positionen_h), sobald
        eine Linie gezogen wird. `zoomGeaendert` feuert mit dem neuen
        Zoomfaktor (1.0 = eingepasst).

    EN: Displays a page with overlaid, draggable cut lines (vertical and
        horizontal at once), zoomable and pannable. `linienGeaendert` fires
        with (positionen_v, positionen_h) whenever a line is dragged.
        `zoomGeaendert` fires with the new zoom factor (1.0 = fitted).
    """

    linienGeaendert = Signal(list, list)
    zoomGeaendert = Signal(float)
    # DE: Feuert einmal, wenn tatsaechlich eine Linie zum Ziehen gegriffen
    #     wurde -- fuer Rueckgaengig/Wiederholen, damit nur einmal pro
    #     Ziehbewegung gesichert wird.
    # EN: Fires once when a line is actually grabbed for dragging -- for
    #     undo/redo, so saving happens once per drag gesture.
    ziehenBegonnen = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)  # DE: fuer Hover-Cursor ohne gedrueckte Taste / EN: for hover cursor without a pressed button
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._pixmap: QPixmap | None = None
        self._positionen_v: list[float] = []
        self._positionen_h: list[float] = []
        self._bild_rect = QRectF()
        self._drag: tuple[str, int] | None = None  # ("v"|"h", index)
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)  # DE: zusaetzlicher Versatz in Bildschirmpixeln / EN: extra offset in screen pixels

    # -- Zustand setzen / setting state --------------------------------

    def seite_setzen(self, pixmap: QPixmap | None, positionen_v: list[float], positionen_h: list[float]) -> None:
        self._pixmap = pixmap
        self._positionen_v = list(positionen_v)
        self._positionen_h = list(positionen_h)
        self._einpassen()

    def positionen(self) -> tuple[list[float], list[float]]:
        return list(self._positionen_v), list(self._positionen_h)

    # -- Zoom / Verschieben / zoom / pan -----------------------------------

    def einpassen(self) -> None:
        """DE: Zoom und Verschiebung zuruecksetzen. EN: Reset zoom and pan."""
        self._einpassen()

    def _einpassen(self) -> None:
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)
        self.zoomGeaendert.emit(self._zoom)
        self.update()

    def zoom_schritt(self, faktor: float) -> None:
        """DE: Um den Widget-Mittelpunkt herum zoomen (z. B. per Knopf).
        EN: Zoom around the widget's center (e.g. via a button)."""
        mitte = QPointF(self.width() / 2, self.height() / 2)
        self._zoom_setzen(self._zoom * faktor, mitte)

    def _zoom_setzen(self, neuer_zoom: float, anker: QPointF) -> None:
        """DE: Zoomen, so dass der Bildpunkt unter `anker` an derselben
        Bildschirmstelle stehen bleibt (Zoom "unter dem Mauszeiger").
        EN: Zoom so the image point under `anker` stays at the same screen
        position (zoom "under the cursor")."""
        neuer_zoom = max(_ZOOM_MIN, min(_ZOOM_MAX, neuer_zoom))
        if abs(neuer_zoom - self._zoom) < 1e-9:
            return
        vorher = self._bild_rechteck()
        if vorher.width() <= 0 or vorher.height() <= 0:
            self._zoom = neuer_zoom
            self.zoomGeaendert.emit(self._zoom)
            self.update()
            return
        rel_x = (anker.x() - vorher.left()) / vorher.width()
        rel_y = (anker.y() - vorher.top()) / vorher.height()

        self._zoom = neuer_zoom
        nachher = self._bild_rechteck()
        ziel_x = nachher.left() + rel_x * nachher.width()
        ziel_y = nachher.top() + rel_y * nachher.height()
        self._pan += QPointF(anker.x() - ziel_x, anker.y() - ziel_y)

        self.zoomGeaendert.emit(self._zoom)
        self.update()

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # DE: Trackpad-Pinch liefert Qt unter macOS als Strg+Scrollen.
            # EN: Trackpad pinch is delivered by Qt on macOS as Ctrl+scroll.
            self._zoom_setzen(self._zoom * (1.0015 ** event.angleDelta().y()), event.position())
        else:
            delta = event.pixelDelta() if not event.pixelDelta().isNull() else event.angleDelta() / 8
            self._pan += QPointF(delta.x(), delta.y())
            self.update()
        event.accept()

    # -- Zeichnen / painting ---------------------------------------------

    def _bild_rechteck(self) -> QRectF:
        """DE: Rechteck, in dem das Bild tatsaechlich angezeigt wird (skaliert, zentriert, gezoomt, verschoben).
        EN: Rectangle in which the image is actually displayed (scaled, centered, zoomed, panned)."""
        if self._pixmap is None or self._pixmap.isNull():
            return QRectF()
        verfuegbar_b = self.width() * 0.9
        verfuegbar_h = self.height() * 0.9
        faktor = min(verfuegbar_b / self._pixmap.width(), verfuegbar_h / self._pixmap.height()) * self._zoom
        breite = self._pixmap.width() * faktor
        hoehe = self._pixmap.height() * faktor
        x = (self.width() - breite) / 2 + self._pan.x()
        y = (self.height() - hoehe) / 2 + self._pan.y()
        return QRectF(x, y, breite, hoehe)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        self._bild_rect = self._bild_rechteck()
        if self._pixmap is not None and not self._pixmap.isNull():
            painter.drawPixmap(self._bild_rect, self._pixmap, QRectF(self._pixmap.rect()))

        painter.setPen(QPen(QColor(255, 210, 0, 230), 2, Qt.PenStyle.SolidLine))
        for p in self._positionen_v:
            x = self._bild_rect.left() + p * self._bild_rect.width()
            painter.drawLine(int(x), int(self._bild_rect.top()), int(x), int(self._bild_rect.bottom()))
        for p in self._positionen_h:
            y = self._bild_rect.top() + p * self._bild_rect.height()
            painter.drawLine(int(self._bild_rect.left()), int(y), int(self._bild_rect.right()), int(y))

    # -- Maus-Drag zum Verschieben einer Linie / mouse-drag to move a line --

    def _treffer(self, pos) -> tuple[str, int] | None:
        """DE: Naechstgelegene Linie innerhalb der Trefftoleranz finden, egal welcher Achse.
        EN: Find the nearest line within the hit tolerance, regardless of axis."""
        if self._bild_rect.isEmpty():
            return None
        kandidaten: list[tuple[float, tuple[str, int]]] = []
        for i, p in enumerate(self._positionen_v):
            x = self._bild_rect.left() + p * self._bild_rect.width()
            kandidaten.append((abs(pos.x() - x), ("v", i)))
        for i, p in enumerate(self._positionen_h):
            y = self._bild_rect.top() + p * self._bild_rect.height()
            kandidaten.append((abs(pos.y() - y), ("h", i)))
        if not kandidaten:
            return None
        abstand, treffer = min(kandidaten, key=lambda t: t[0])
        return treffer if abstand <= _TREFFER_ABSTAND else None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = self._treffer(event.position())
            if self._drag is not None:
                self.ziehenBegonnen.emit()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is None:
            treffer = self._treffer(event.position())
            if treffer is None:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif treffer[0] == "v":
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            return

        achse, i = self._drag
        pos = event.position()
        liste = self._positionen_v if achse == "v" else self._positionen_h
        if achse == "v":
            anteil = (pos.x() - self._bild_rect.left()) / self._bild_rect.width()
        else:
            anteil = (pos.y() - self._bild_rect.top()) / self._bild_rect.height()

        untere_grenze = liste[i - 1] + _MINDESTABSTAND if i > 0 else _MINDESTABSTAND
        obere_grenze = liste[i + 1] - _MINDESTABSTAND if i + 1 < len(liste) else 1 - _MINDESTABSTAND
        liste[i] = max(untere_grenze, min(obere_grenze, anteil))

        self.update()
        self.linienGeaendert.emit(list(self._positionen_v), list(self._positionen_h))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = None
