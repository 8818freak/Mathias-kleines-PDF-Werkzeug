"""
DE: Interaktive Vorschauflaeche fuer das Zuschneiden-Werkzeug. Zeigt eine
    Seite (bereits inkl. ihrer Drehung/Spiegelung) gross an, mit einem
    Beschnitt-Rechteck darueber -- vier Linien, je eine pro Rand. Der
    Bereich AUSSERHALB des Rechtecks (der abgeschnitten wuerde) wird
    abgedunkelt dargestellt, damit sofort sichtbar ist, was uebrig
    bleibt. Jede Linie laesst sich einzeln per Maus-Drag entlang ihrer
    Achse verschieben. Zoom/Verschieben wie beim Teilen-Werkzeug (Strg/
    Cmd+Scrollen bzw. Pinch-Geste, verankert am Mauszeiger; einfaches
    Scrollen/Wischen zum Verschieben) -- wichtig fuer praezises Treffen
    bei kleinen Randmassen.

EN: Interactive preview area for the crop tool. Displays a page (already
    including its rotation/mirror) at large size, with a crop rectangle
    overlaid -- four lines, one per edge. The area OUTSIDE the rectangle
    (which would be cut away) is darkened, so it's immediately visible
    what remains. Each line can be dragged individually along its axis.
    Zoom/pan work like in the split tool (Ctrl/Cmd+scroll resp. pinch
    gesture, anchored at the cursor; plain scroll/swipe to pan) --
    important for precise hits with small margins.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

# DE: Abstand in Pixeln, innerhalb dessen ein Klick eine Linie trifft.
# EN: Distance in pixels within which a click hits a line.
_TREFFER_ABSTAND = 12.0
# DE: Mindestabstand zwischen zwei gegenueberliegenden Linien, als Anteil (0..1).
# EN: Minimum spacing between two opposing lines, as a fraction (0..1).
_MINDESTABSTAND = 0.02
# DE: Erlaubter Zoombereich. EN: Allowed zoom range.
_ZOOM_MIN = 1.0
_ZOOM_MAX = 40.0
# DE: Abdunkelung des abgeschnittenen Bereichs (Alpha 0..255).
# EN: Darkening of the cropped-away area (alpha 0..255).
_ABDUNKELUNG_ALPHA = 150


class ZuschneidenCanvas(QWidget):
    """
    DE: Zeigt eine Seite mit ueberlagertem, verschiebbarem Beschnitt-
        Rechteck, zoom- und verschiebbar. `raenderGeaendert` feuert mit
        (links, oben, rechts, unten) als Anteile (0..1) der jeweiligen
        Kantenlaenge, sobald eine Linie gezogen wird. `zoomGeaendert`
        feuert mit dem neuen Zoomfaktor (1.0 = eingepasst).

    EN: Displays a page with an overlaid, draggable crop rectangle,
        zoomable and pannable. `raenderGeaendert` fires with (left, top,
        right, bottom) as fractions (0..1) of the respective edge
        length, whenever a line is dragged. `zoomGeaendert` fires with
        the new zoom factor (1.0 = fitted).
    """

    raenderGeaendert = Signal(float, float, float, float)
    zoomGeaendert = Signal(float)
    # DE: Feuert einmal, wenn tatsaechlich eine Linie zum Ziehen gegriffen
    #     wurde -- fuer Rueckgaengig/Wiederholen.
    # EN: Fires once when a line is actually grabbed for dragging -- for
    #     undo/redo.
    ziehenBegonnen = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._pixmap: QPixmap | None = None
        self._links = 0.0
        self._oben = 0.0
        self._rechts = 0.0
        self._unten = 0.0
        self._bild_rect = QRectF()
        self._drag: str | None = None  # "links"|"oben"|"rechts"|"unten"
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)

    # -- Zustand setzen / setting state --------------------------------

    def seite_setzen(self, pixmap: QPixmap | None, links: float, oben: float, rechts: float, unten: float) -> None:
        self._pixmap = pixmap
        self._links, self._oben, self._rechts, self._unten = links, oben, rechts, unten
        self._einpassen()

    def raender_setzen(self, links: float, oben: float, rechts: float, unten: float) -> None:
        """DE: Raender von aussen (z. B. aus den Zahlenfeldern) uebernehmen,
        ohne Zoom/Verschiebung zu aendern.
        EN: Take margins from outside (e.g. from the number fields),
        without changing zoom/pan."""
        self._links, self._oben, self._rechts, self._unten = links, oben, rechts, unten
        self.update()

    def raender(self) -> tuple[float, float, float, float]:
        return self._links, self._oben, self._rechts, self._unten

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
            self._zoom_setzen(self._zoom * (1.0015 ** event.angleDelta().y()), event.position())
        else:
            delta = event.pixelDelta() if not event.pixelDelta().isNull() else event.angleDelta() / 8
            self._pan += QPointF(delta.x(), delta.y())
            self.update()
        event.accept()

    # -- Zeichnen / painting ---------------------------------------------

    def _bild_rechteck(self) -> QRectF:
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

        r = self._bild_rect
        x_links = r.left() + self._links * r.width()
        x_rechts = r.right() - self._rechts * r.width()
        y_oben = r.top() + self._oben * r.height()
        y_unten = r.bottom() - self._unten * r.height()

        # DE: Abgeschnittenen Bereich abdunkeln -- vier Streifen aussen
        #     um das (unveraenderte) Beschnitt-Rechteck herum.
        # EN: Darken the cropped-away area -- four strips outside the
        #     (unaltered) crop rectangle.
        abdunklung = QColor(0, 0, 0, _ABDUNKELUNG_ALPHA)
        painter.fillRect(QRectF(r.left(), r.top(), r.width(), y_oben - r.top()), abdunklung)
        painter.fillRect(QRectF(r.left(), y_unten, r.width(), r.bottom() - y_unten), abdunklung)
        painter.fillRect(QRectF(r.left(), y_oben, x_links - r.left(), y_unten - y_oben), abdunklung)
        painter.fillRect(QRectF(x_rechts, y_oben, r.right() - x_rechts, y_unten - y_oben), abdunklung)

        painter.setPen(QPen(QColor(255, 210, 0, 230), 2, Qt.PenStyle.SolidLine))
        painter.drawRect(QRectF(x_links, y_oben, x_rechts - x_links, y_unten - y_oben))

    # -- Maus-Drag zum Verschieben einer Linie / mouse-drag to move a line --

    def _treffer(self, pos) -> str | None:
        """DE: Naechstgelegene Randlinie innerhalb der Trefftoleranz finden.
        EN: Find the nearest edge line within the hit tolerance."""
        if self._bild_rect.isEmpty():
            return None
        r = self._bild_rect
        x_links = r.left() + self._links * r.width()
        x_rechts = r.right() - self._rechts * r.width()
        y_oben = r.top() + self._oben * r.height()
        y_unten = r.bottom() - self._unten * r.height()
        kandidaten = [
            (abs(pos.x() - x_links), "links"),
            (abs(pos.x() - x_rechts), "rechts"),
            (abs(pos.y() - y_oben), "oben"),
            (abs(pos.y() - y_unten), "unten"),
        ]
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
            elif treffer in ("links", "rechts"):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            return

        pos = event.position()
        r = self._bild_rect
        if self._drag == "links":
            anteil = (pos.x() - r.left()) / r.width()
            self._links = max(0.0, min(1 - self._rechts - _MINDESTABSTAND, anteil))
        elif self._drag == "rechts":
            anteil = (r.right() - pos.x()) / r.width()
            self._rechts = max(0.0, min(1 - self._links - _MINDESTABSTAND, anteil))
        elif self._drag == "oben":
            anteil = (pos.y() - r.top()) / r.height()
            self._oben = max(0.0, min(1 - self._unten - _MINDESTABSTAND, anteil))
        else:
            anteil = (r.bottom() - pos.y()) / r.height()
            self._unten = max(0.0, min(1 - self._oben - _MINDESTABSTAND, anteil))

        self.update()
        self.raenderGeaendert.emit(self._links, self._oben, self._rechts, self._unten)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = None
