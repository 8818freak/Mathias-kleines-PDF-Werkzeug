"""
DE: Interaktive Vorschauflaeche fuer das Zusammenfuegen-Werkzeug. Zeigt
    alle Kacheln (Teile) an ihrer jeweiligen Position auf einer
    gemeinsamen Leinwand -- anklicken waehlt eine Kachel aus (gelb
    umrandet), Ziehen verschiebt sie frei. Drehung und Beschnitt werden
    nicht auf der Leinwand gezogen, sondern ueber Zahlenfelder im
    Werkzeug eingestellt (fuer technische Zeichnungen praeziser als
    Mausziehen) -- die Leinwand zeigt dabei aber sofort das Ergebnis, da
    das Werkzeug bei jeder Aenderung ein neu berechnetes Vorschaubild
    liefert.

    Wie beim Teilen-Werkzeug per Strg/Cmd+Scrollen bzw. Pinch-Geste
    zoombar (am Mauszeiger verankert) und per Scrollen/Wischen
    verschiebbar.

EN: Interactive preview area for the combine tool. Shows all tiles at
    their respective position on a shared canvas -- clicking selects a
    tile (yellow outline), dragging moves it freely. Rotation and crop
    are not dragged on the canvas but set via numeric fields in the tool
    (more precise for technical drawings than mouse dragging) -- the
    canvas still shows the result immediately though, since the tool
    supplies a freshly rendered preview image on every change.

    Zoomable (Ctrl/Cmd+scroll or trackpad pinch, anchored at the cursor)
    and pannable (plain scroll/swipe), like the split tool.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

_ZOOM_MIN = 1.0
_ZOOM_MAX = 40.0


@dataclass
class _KachelEintrag:
    index: int
    x_pt: float
    y_pt: float
    breite_pt: float
    hoehe_pt: float
    pixmap: QPixmap


class ZusammenfuegenCanvas(QWidget):
    """
    DE: Zeigt mehrere frei positionierbare Kacheln auf einer gemeinsamen,
        zoom-/verschiebbaren Leinwand. `kachelAusgewaehlt` feuert mit dem
        Kachel-Index (-1 = keine Auswahl). `kachelVerschoben` feuert mit
        (index, neues_x_pt, neues_y_pt) waehrend des Ziehens.
        `verschiebenBegonnen` feuert einmal zu Beginn einer Ziehbewegung.

    EN: Displays several freely positionable tiles on a shared, zoomable/
        pannable canvas. `kachelAusgewaehlt` fires with the tile index
        (-1 = no selection). `kachelVerschoben` fires with
        (index, new_x_pt, new_y_pt) while dragging. `verschiebenBegonnen`
        fires once at the start of a drag.
    """

    kachelAusgewaehlt = Signal(int)
    kachelVerschoben = Signal(int, float, float)
    zoomGeaendert = Signal(float)
    verschiebenBegonnen = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._kacheln: list[_KachelEintrag] = []
        self._ausgewaehlt = -1
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)
        self._drag: tuple[int, QPointF, float, float] | None = None  # (index, maus_start, x_pt_start, y_pt_start)

    # -- Zustand setzen / setting state --------------------------------

    def kacheln_setzen(self, eintraege: list[tuple[int, float, float, float, float, QPixmap]]) -> None:
        """DE: Alle Kacheln komplett neu setzen (z. B. nach „Anordnung erzeugen“), Ansicht einpassen.
        EN: Fully replace all tiles (e.g. after "generate layout"), fit the view."""
        self._kacheln = [_KachelEintrag(*e) for e in eintraege]
        self._einpassen()

    def kachel_aktualisieren(self, index: int, x_pt: float, y_pt: float,
                             breite_pt: float, hoehe_pt: float, pixmap: QPixmap) -> None:
        """DE: Eine einzelne Kachel aktualisieren (Position/Groesse/Bild), ohne Zoom/Pan zu veraendern.
        EN: Update a single tile (position/size/image) without changing zoom/pan."""
        for eintrag in self._kacheln:
            if eintrag.index == index:
                eintrag.x_pt, eintrag.y_pt = x_pt, y_pt
                eintrag.breite_pt, eintrag.hoehe_pt = breite_pt, hoehe_pt
                eintrag.pixmap = pixmap
                self.update()
                return

    def ausgewaehlter_index(self) -> int:
        """DE: Index der aktuell ausgewaehlten Kachel, -1 wenn keine.
        EN: Index of the currently selected tile, -1 if none."""
        return self._ausgewaehlt

    def auswahl_setzen(self, index: int) -> None:
        """DE: Auswahl von aussen setzen (z. B. -1 nach dem Leeren), ohne Signal auszuloesen.
        EN: Set the selection from the outside (e.g. -1 after clearing), without firing a signal."""
        self._ausgewaehlt = index
        self.update()

    # -- Zoom / Verschieben / zoom / pan -----------------------------------

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
        vorher = self._dokument_rechteck()
        if vorher.width() <= 0 or vorher.height() <= 0:
            self._zoom = neuer_zoom
            self.zoomGeaendert.emit(self._zoom)
            self.update()
            return
        rel_x = (anker.x() - vorher.left()) / vorher.width()
        rel_y = (anker.y() - vorher.top()) / vorher.height()
        self._zoom = neuer_zoom
        nachher = self._dokument_rechteck()
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

    # -- Koordinatenumrechnung / coordinate mapping ------------------------

    def _dokument_grenzen_pt(self) -> QRectF:
        """DE: Umschliessendes Rechteck aller Kacheln in Dokument-Punkten.
        EN: Bounding rectangle of all tiles, in document points."""
        if not self._kacheln:
            return QRectF()
        min_x = min(k.x_pt for k in self._kacheln)
        min_y = min(k.y_pt for k in self._kacheln)
        max_x = max(k.x_pt + k.breite_pt for k in self._kacheln)
        max_y = max(k.y_pt + k.hoehe_pt for k in self._kacheln)
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def _dokument_rechteck(self) -> QRectF:
        """DE: Bildschirmrechteck, in dem die gesamte Dokumentflaeche dargestellt wird.
        EN: Screen rectangle in which the whole document area is displayed."""
        grenzen = self._dokument_grenzen_pt()
        if grenzen.width() <= 0 or grenzen.height() <= 0:
            return QRectF()
        verfuegbar_b = self.width() * 0.9
        verfuegbar_h = self.height() * 0.9
        faktor = min(verfuegbar_b / grenzen.width(), verfuegbar_h / grenzen.height()) * self._zoom
        breite = grenzen.width() * faktor
        hoehe = grenzen.height() * faktor
        x = (self.width() - breite) / 2 + self._pan.x()
        y = (self.height() - hoehe) / 2 + self._pan.y()
        return QRectF(x, y, breite, hoehe)

    def _kachel_rechteck(self, eintrag: _KachelEintrag, dok_rect: QRectF, grenzen: QRectF) -> QRectF:
        """DE: Bildschirmrechteck einer Kachel. EN: Screen rectangle of a tile."""
        if grenzen.width() <= 0 or grenzen.height() <= 0:
            return QRectF()
        x = dok_rect.left() + (eintrag.x_pt - grenzen.left()) / grenzen.width() * dok_rect.width()
        y = dok_rect.top() + (eintrag.y_pt - grenzen.top()) / grenzen.height() * dok_rect.height()
        b = eintrag.breite_pt / grenzen.width() * dok_rect.width()
        h = eintrag.hoehe_pt / grenzen.height() * dok_rect.height()
        return QRectF(x, y, b, h)

    # -- Zeichnen / painting ---------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        if not self._kacheln:
            # DE: Leerer Zustand ist sonst nur eine leere dunkle Flaeche --
            #     ohne Hinweis nicht erkennbar, dass hier gleich die
            #     Anordnung erscheint, sobald man den Knopf oben gedrueckt hat.
            # EN: The empty state is otherwise just a blank dark area --
            #     without a hint it's not obvious that the layout will show
            #     up here once the button above has been pressed.
            painter.setPen(QColor(255, 255, 255, 140))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                "Noch keine Anordnung.\n\nLinks mindestens zwei Seiten auswählen,\n"
                "dann oben auf „Anordnung aus Auswahl erzeugen“ klicken.",
            )
            return

        dok_rect = self._dokument_rechteck()
        grenzen = self._dokument_grenzen_pt()
        for eintrag in self._kacheln:
            rect = self._kachel_rechteck(eintrag, dok_rect, grenzen)
            if not eintrag.pixmap.isNull():
                painter.drawPixmap(rect, eintrag.pixmap, QRectF(eintrag.pixmap.rect()))
            if eintrag.index == self._ausgewaehlt:
                painter.setPen(QPen(QColor(255, 210, 0, 230), 3, Qt.PenStyle.SolidLine))
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 90), 1, Qt.PenStyle.SolidLine))
            painter.drawRect(rect)

    # -- Maus: Auswaehlen und Verschieben / mouse: select and move --------

    def _treffer(self, pos: QPointF) -> int:
        """DE: Index der obersten (zuletzt gezeichneten) Kachel unter `pos`, oder -1.
        EN: Index of the topmost (last-drawn) tile under `pos`, or -1."""
        dok_rect = self._dokument_rechteck()
        grenzen = self._dokument_grenzen_pt()
        for eintrag in reversed(self._kacheln):
            if self._kachel_rechteck(eintrag, dok_rect, grenzen).contains(pos):
                return eintrag.index
        return -1

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        index = self._treffer(event.position())
        if index != self._ausgewaehlt:
            self._ausgewaehlt = index
            self.kachelAusgewaehlt.emit(index)
            self.update()
        if index != -1:
            eintrag = next(k for k in self._kacheln if k.index == index)
            self.verschiebenBegonnen.emit()
            self._drag = (index, event.position(), eintrag.x_pt, eintrag.y_pt)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is None:
            return
        index, start_pos, start_x_pt, start_y_pt = self._drag
        dok_rect = self._dokument_rechteck()
        grenzen = self._dokument_grenzen_pt()
        if dok_rect.width() <= 0 or grenzen.width() <= 0:
            return
        skala_pt_pro_px = grenzen.width() / dok_rect.width()
        delta = event.position() - start_pos
        neues_x = start_x_pt + delta.x() * skala_pt_pro_px
        neues_y = start_y_pt + delta.y() * skala_pt_pro_px
        for eintrag in self._kacheln:
            if eintrag.index == index:
                eintrag.x_pt, eintrag.y_pt = neues_x, neues_y
                break
        self.update()
        self.kachelVerschoben.emit(index, neues_x, neues_y)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = None
