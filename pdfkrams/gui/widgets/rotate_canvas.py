"""
DE: Interaktive Vorschauflaeche fuer das Dreh-Werkzeug. Zeigt eine Seite
    gross an; per Klicken-und-Ziehen mit der Maus laesst sie sich frei
    drehen (wie an einem Rad), waehrenddessen helfen feste, farbige
    Referenzlinien (waagerecht UND senkrecht) beim Beurteilen, ob die
    Seite schon gerade ist -- die Farbe laesst sich von aussen einstellen
    (siehe linienfarbe_setzen()/rotate_tool.py), z. B. passend zur
    Seitenfarbe. Zusaetzlich per Pfeiltasten in 0.1°-Schritten (mit
    Umschalt-Taste 1°-Schritte) feinjustierbar. Zoom/Verschieben wie bei
    den anderen Werkzeugen (Strg/Cmd+Scrollen bzw. Pinch-Geste, verankert
    am Mauszeiger; einfaches Scrollen/Wischen zum Verschieben) -- das
    Drehen selbst bleibt dabei immer um die Mitte der (ggf. verschobenen)
    Seite verankert, nicht um die Fenstermitte.

EN: Interactive preview area for the rotate tool. Displays a page at large
    size; click-and-drag with the mouse rotates it freely (like turning a
    wheel), while fixed, colored reference lines (horizontal AND
    vertical) help judge whether the page is level yet -- the color can
    be configured from the outside (see linienfarbe_setzen()/
    rotate_tool.py), e.g. to match the page color. Also fine-adjustable
    via arrow keys in 0.1° steps (1° steps with the Shift key). Zoom/pan
    work like in the other tools (Ctrl/Cmd+scroll resp. pinch gesture,
    anchored at the cursor; plain scroll/swipe to pan) -- rotation itself
    always stays anchored to the center of the (possibly panned) page,
    not the widget center.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from pdfkrams.core.rotate import normalisiert

# DE: Abstand der Referenzlinien (waagerecht + senkrecht) in Pixeln.
# EN: Spacing of the reference lines (horizontal + vertical) in pixels.
_RASTER_ABSTAND = 20
_ZOOM_MIN = 1.0
_ZOOM_MAX = 40.0

# DE: Standardfarbe der Referenzlinien -- von aussen per linienfarbe_setzen()
#     aenderbar (siehe rotate_tool.py), z. B. weil Rot auf einer bräunlichen
#     Seite kaum zu erkennen ist.
# EN: Default color of the reference lines -- changeable from the outside
#     via linienfarbe_setzen() (see rotate_tool.py), e.g. because red is
#     hard to make out on a brownish page.
_STANDARD_LINIENFARBE = QColor(255, 70, 70)


class RotateCanvas(QWidget):
    """
    DE: Zeigt eine Seite drehbar/spiegelbar an. Die Drehung wird per Maus-
        Drag live veraendert (`winkelGeaendert` feuert bei jeder Aenderung);
        Spiegelung wird nur von aussen gesetzt (ueber die Schnellaktionen im
        Werkzeug), nicht per Maus.

    EN: Displays a page that can be rotated/mirrored. Rotation changes live
        via mouse drag (`winkelGeaendert` fires on every change); mirroring
        is only set from the outside (via the tool's quick actions), not
        via the mouse.
    """

    winkelGeaendert = Signal(float)
    # DE: Feuert einmal zu Beginn einer Ziehbewegung bzw. Tastendruck-Serie
    #     -- fuer Rueckgaengig/Wiederholen, damit nur einmal pro Geste
    #     gesichert wird statt bei jeder einzelnen Zwischenaenderung.
    # EN: Fires once at the start of a drag resp. key-press series -- for
    #     undo/redo, so saving happens once per gesture instead of on every
    #     single intermediate change.
    aenderungBegonnen = Signal()
    zoomGeaendert = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self._pixmap: QPixmap | None = None
        self._winkel = 0.0
        self._spiegel_h = False
        self._spiegel_v = False
        self._drag_aktiv = False
        self._drag_start_maus_winkel = 0.0
        self._drag_start_seiten_winkel = 0.0
        self._taste_aktiv = False
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)
        self._linienfarbe = QColor(_STANDARD_LINIENFARBE)

    def linienfarbe_setzen(self, farbe: QColor) -> None:
        """DE: Farbe der Referenzlinien (Wasserwaage) aendern -- z. B.
            passend zur Seitenfarbe, damit die Linien gut zu erkennen sind.
        EN: Change the color of the reference lines (spirit level) -- e.g.
            to match the page color, so the lines are easy to make out."""
        self._linienfarbe = farbe
        self.update()

    # -- Zustand setzen / setting state --------------------------------

    def seite_setzen(self, pixmap: QPixmap | None, winkel: float, spiegel_h: bool, spiegel_v: bool) -> None:
        """DE: Neue Seite laden, ohne winkelGeaendert auszuloesen (Initialisierung).
            Setzt Zoom/Verschiebung zurueck (neue Seite = frische Ansicht).
        EN: Load a new page without triggering winkelGeaendert (initialization).
            Resets zoom/pan (new page = fresh view)."""
        self._pixmap = pixmap
        self._winkel = winkel
        self._spiegel_h = spiegel_h
        self._spiegel_v = spiegel_v
        self._einpassen()

    def winkel(self) -> float:
        return self._winkel

    def winkel_setzen(self, winkel: float) -> None:
        """DE: Winkel von aussen setzen (z. B. aus dem Zahlenfeld), loest winkelGeaendert aus.
        EN: Set the angle from the outside (e.g. from the spinbox), triggers winkelGeaendert."""
        winkel = normalisiert(winkel)
        if abs(winkel - self._winkel) > 1e-9:
            self._winkel = winkel
            self.update()
            self.winkelGeaendert.emit(self._winkel)

    # -- Zoom / Verschieben / zoom / pan -----------------------------------
    # DE: Wie bei den anderen Werkzeugen (z. B. ZuschneidenCanvas) -- siehe
    #     dort fuer Erklaerungen. Der Anker fuer den Zoom ignoriert bewusst
    #     die aktuelle Drehung (rein bildschirmraum-basiert) -- bei den
    #     hier ueblichen kleinen Korrekturwinkeln praktisch nicht
    #     wahrnehmbar, dafuer deutlich einfacher als eine drehkorrigierte
    #     Ankerrechnung.
    # EN: Like the other tools (e.g. ZuschneidenCanvas) -- see there for
    #     explanations. The zoom anchor deliberately ignores the current
    #     rotation (purely screen-space based) -- practically unnoticeable
    #     at the small correction angles typical here, while being much
    #     simpler than a rotation-corrected anchor calculation.

    def einpassen(self) -> None:
        self._einpassen()

    def _einpassen(self) -> None:
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)
        self.zoomGeaendert.emit(self._zoom)
        self.update()

    def zoom_schritt(self, faktor: float) -> None:
        mitte = QPointF(self.width() / 2, self.height() / 2)
        self._zoom_setzen(self._zoom * faktor, mitte)

    def _zoom_setzen(self, neuer_zoom: float, anker: QPointF) -> None:
        neuer_zoom = max(_ZOOM_MIN, min(_ZOOM_MAX, neuer_zoom))
        if abs(neuer_zoom - self._zoom) < 1e-9:
            return
        basis = QPointF(self.width() / 2, self.height() / 2)
        mitte_vorher = basis + self._pan
        rel_x = (anker.x() - mitte_vorher.x()) / self._zoom
        rel_y = (anker.y() - mitte_vorher.y()) / self._zoom

        self._zoom = neuer_zoom
        mitte_nachher = basis + self._pan
        ziel = QPointF(mitte_nachher.x() + rel_x * neuer_zoom, mitte_nachher.y() + rel_y * neuer_zoom)
        self._pan += QPointF(anker.x() - ziel.x(), anker.y() - ziel.y())

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

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        mitte = QPointF(self.width() / 2 + self._pan.x(), self.height() / 2 + self._pan.y())

        if self._pixmap is not None and not self._pixmap.isNull():
            # DE: Anzeigegroesse an das Widget anpassen, Seitenverhaeltnis
            #     erhalten, mit Zoomfaktor multipliziert.
            # EN: Fit display size to the widget, preserving aspect ratio,
            #     multiplied by the zoom factor.
            verfuegbar = min(self.width(), self.height()) * 0.85
            faktor = verfuegbar / max(self._pixmap.width(), self._pixmap.height()) * self._zoom
            breite = self._pixmap.width() * faktor
            hoehe = self._pixmap.height() * faktor

            painter.save()
            painter.translate(mitte)
            painter.rotate(self._winkel)
            if self._spiegel_h:
                painter.scale(-1, 1)
            if self._spiegel_v:
                painter.scale(1, -1)
            ziel = QRectF(-breite / 2, -hoehe / 2, breite, hoehe)
            painter.drawPixmap(ziel, self._pixmap, QRectF(self._pixmap.rect()))
            painter.restore()

        # DE: Feste, nicht mitgedrehte Referenzlinien als Wasserwaage --
        #     waagerecht UND senkrecht, damit sich auch an senkrechten
        #     Kanten (Spaltenraender, Buchruecken) ausrichten laesst.
        # EN: Fixed reference lines that don't rotate, as a spirit level
        #     -- horizontal AND vertical, so alignment also works against
        #     vertical edges (column margins, book spines).
        raster_farbe = QColor(self._linienfarbe)
        raster_farbe.setAlpha(150)
        painter.setPen(QPen(raster_farbe, 1, Qt.PenStyle.DashLine))
        y = int(mitte.y()) % _RASTER_ABSTAND
        while y < self.height():
            painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
            y += _RASTER_ABSTAND
        x = int(mitte.x()) % _RASTER_ABSTAND
        while x < self.width():
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            x += _RASTER_ABSTAND
        mitte_farbe = QColor(self._linienfarbe)
        mitte_farbe.setAlpha(220)
        painter.setPen(QPen(mitte_farbe, 1, Qt.PenStyle.SolidLine))
        painter.drawLine(QPointF(0, mitte.y()), QPointF(self.width(), mitte.y()))
        painter.drawLine(QPointF(mitte.x(), 0), QPointF(mitte.x(), self.height()))

    # -- Maus-Drag zum Drehen / mouse-drag to rotate ----------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap is not None:
            self.aenderungBegonnen.emit()
            self._drag_aktiv = True
            self._drag_start_maus_winkel = self._maus_winkel(event.position())
            self._drag_start_seiten_winkel = self._winkel
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_aktiv:
            aktuell = self._maus_winkel(event.position())
            delta = aktuell - self._drag_start_maus_winkel
            self.winkel_setzen(self._drag_start_seiten_winkel + delta)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_aktiv = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _maus_winkel(self, pos: QPointF) -> float:
        """DE: Winkel der Mausposition relativ zur (ggf. verschobenen)
            Bildmitte in Grad -- das Drehen bleibt so auch bei aktivem
            Pan intuitiv um die Seite selbst verankert.
        EN: Angle of the mouse position relative to the (possibly panned)
            image center, in degrees -- this keeps rotation intuitively
            anchored to the page itself even while panned."""
        mitte = QPointF(self.width() / 2 + self._pan.x(), self.height() / 2 + self._pan.y())
        return math.degrees(math.atan2(pos.y() - mitte.y(), pos.x() - mitte.x()))

    # -- Feinjustierung per Tastatur / keyboard fine-tuning ---------------

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() not in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            super().keyPressEvent(event)
            return
        if not event.isAutoRepeat() and not self._taste_aktiv:
            self._taste_aktiv = True
            self.aenderungBegonnen.emit()
        schritt = 1.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 0.1
        if event.key() == Qt.Key.Key_Left:
            self.winkel_setzen(self._winkel - schritt)
        else:
            self.winkel_setzen(self._winkel + schritt)

    def keyReleaseEvent(self, event) -> None:  # noqa: N802
        if not event.isAutoRepeat() and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self._taste_aktiv = False
        super().keyReleaseEvent(event)
