"""
DE: Interaktive Vorschauflaeche fuer das Dreh-Werkzeug. Zeigt eine Seite
    gross an; per Klicken-und-Ziehen mit der Maus laesst sie sich frei
    drehen (wie an einem Rad), waehrenddessen helfen feste rote
    Referenzlinien beim Beurteilen, ob die Seite schon gerade ist. Zusaetzlich
    per Pfeiltasten in 0.1°-Schritten (mit Umschalt-Taste 1°-Schritte)
    feinjustierbar.

EN: Interactive preview area for the rotate tool. Displays a page at large
    size; click-and-drag with the mouse rotates it freely (like turning a
    wheel), while fixed red reference lines help judge whether the page is
    level yet. Also fine-adjustable via arrow keys in 0.1° steps (1° steps
    with the Shift key).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from pdfkrams.core.rotate import normalisiert

# DE: Abstand der horizontalen Referenzlinien in Pixeln.
# EN: Spacing of the horizontal reference lines in pixels.
_RASTER_ABSTAND = 40


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

    # -- Zustand setzen / setting state --------------------------------

    def seite_setzen(self, pixmap: QPixmap | None, winkel: float, spiegel_h: bool, spiegel_v: bool) -> None:
        """DE: Neue Seite laden, ohne winkelGeaendert auszuloesen (Initialisierung).
        EN: Load a new page without triggering winkelGeaendert (initialization)."""
        self._pixmap = pixmap
        self._winkel = winkel
        self._spiegel_h = spiegel_h
        self._spiegel_v = spiegel_v
        self.update()

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

    # -- Zeichnen / painting ---------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        mitte = QPointF(self.width() / 2, self.height() / 2)

        if self._pixmap is not None and not self._pixmap.isNull():
            # DE: Anzeigegroesse an das Widget anpassen, Seitenverhaeltnis erhalten.
            # EN: Fit display size to the widget, preserving aspect ratio.
            verfuegbar = min(self.width(), self.height()) * 0.85
            faktor = verfuegbar / max(self._pixmap.width(), self._pixmap.height())
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

        # DE: Feste, nicht mitgedrehte Referenzlinien als Waagerecht-Hilfe.
        # EN: Fixed reference lines that don't rotate, as a level-guide.
        painter.setPen(QPen(QColor(255, 70, 70, 150), 1, Qt.PenStyle.DashLine))
        y = int(mitte.y()) % _RASTER_ABSTAND
        while y < self.height():
            painter.drawLine(QPointF(0, y), QPointF(self.width(), y))
            y += _RASTER_ABSTAND
        painter.setPen(QPen(QColor(255, 70, 70, 220), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(QPointF(0, mitte.y()), QPointF(self.width(), mitte.y()))

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
        """DE: Winkel der Mausposition relativ zur Widget-Mitte in Grad.
        EN: Angle of the mouse position relative to the widget center, in degrees."""
        mitte = QPointF(self.width() / 2, self.height() / 2)
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
