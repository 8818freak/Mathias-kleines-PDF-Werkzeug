"""
DE: Interaktive Vorschauflaeche fuer das Schwaerzen-Werkzeug. Zeigt eine
    Seite (bereits inkl. ihrer Drehung/Spiegelung) gross an, mit beliebig
    vielen frei gezeichneten, deckend schwarzen Rechtecken darueber -- so
    sieht man WYSIWYG genau das, was am Ende tatsaechlich unkenntlich
    gemacht wird. Auf leerer Flaeche ziehen zeichnet ein neues Rechteck;
    ein bestehendes anklicken waehlt es aus (blauer Rahmen + Eckgriffe)
    und erlaubt Verschieben (Ziehen im Inneren) bzw. Groessenaendern
    (Ziehen an einer Ecke); Entf/Backspace oder ein Knopf im Werkzeug
    loeschen das ausgewaehlte Rechteck. Zoom/Verschieben wie bei den
    anderen Werkzeugen (Strg/Cmd+Scrollen bzw. Pinch-Geste, verankert am
    Mauszeiger; einfaches Scrollen/Wischen zum Verschieben).

EN: Interactive preview area for the redaction tool. Displays a page
    (already including its rotation/mirror) at large size, with any
    number of freely drawn, fully opaque black rectangles overlaid -- so
    what's shown is exactly what actually gets redacted (WYSIWYG).
    Dragging on empty space draws a new rectangle; clicking an existing
    one selects it (blue outline + corner handles) and allows moving
    (drag inside) resp. resizing (drag a corner); Delete/Backspace or a
    button in the tool remove the selected rectangle. Zoom/pan work like
    in the other tools (Ctrl/Cmd+scroll resp. pinch gesture, anchored at
    the cursor; plain scroll/swipe to pan).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from pdfkrams.einstellungen import einstellungen

# DE: Mindestgroesse (Anteil der jeweiligen Kante), damit ein gezogenes
#     Rechteck als echtes Rechteck zaehlt statt als versehentlicher Klick.
# EN: Minimum size (fraction of the respective edge) for a dragged
#     rectangle to count as a real rectangle instead of an accidental click.
_MINDESTGROESSE = 0.01
# DE: Trefftoleranz fuer Eckgriffe in Pixeln.
# EN: Hit tolerance for corner handles, in pixels.
_GRIFF_TOLERANZ = 12.0
_ZOOM_MIN = 1.0
_ZOOM_MAX = 40.0
_GRIFF_GROESSE = 7.0

Rechteck = tuple[float, float, float, float]  # x0, y0, x1, y1 -- Anteile 0..1


class SchwaerzungsCanvas(QWidget):
    """
    DE: Zeigt eine Seite mit beliebig vielen ueberlagerten, deckend
        schwarzen Rechtecken, zoom- und verschiebbar.
        `schwaerzungenGeaendert` feuert, sobald sich die Rechteckliste
        aendert (Hinzufuegen/Verschieben/Groesse/Loeschen).
        `zoomGeaendert` feuert mit dem neuen Zoomfaktor.

    EN: Displays a page with any number of overlaid, fully opaque black
        rectangles, zoomable and pannable. `schwaerzungenGeaendert` fires
        whenever the rectangle list changes (add/move/resize/delete).
        `zoomGeaendert` fires with the new zoom factor.
    """

    schwaerzungenGeaendert = Signal()
    zoomGeaendert = Signal(float)
    ziehenBegonnen = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        einstellungen.schwaerzungsfarbeGeaendert.connect(self.update)

        self._pixmap: QPixmap | None = None
        self._rechtecke: list[Rechteck] = []
        self._ausgewaehlt: int | None = None
        self._bild_rect = QRectF()
        self._zoom = _ZOOM_MIN
        self._pan = QPointF(0, 0)

        # DE: Ziehzustand -- "neu" (neues Rechteck aufziehen), "verschieben",
        #     oder eine Ecke ("tl"/"tr"/"bl"/"br"); None = kein Ziehen.
        # EN: Drag state -- "neu" (dragging out a new rectangle),
        #     "verschieben" (move), or a corner ("tl"/"tr"/"bl"/"br");
        #     None = not dragging.
        self._ziehen: str | None = None
        self._ziehstart_bild = QPointF()  # DE: Anteile / EN: fractions
        self._ziehstart_rechteck: Rechteck | None = None

    # -- Zustand setzen / setting state --------------------------------

    def seite_setzen(self, pixmap: QPixmap | None, rechtecke: list[Rechteck]) -> None:
        self._pixmap = pixmap
        self._rechtecke = list(rechtecke)
        self._ausgewaehlt = None
        self._einpassen()

    def rechtecke(self) -> list[Rechteck]:
        return list(self._rechtecke)

    def entferne_ausgewaehlte(self) -> bool:
        """DE: Loescht das ausgewaehlte Rechteck, falls eines ausgewaehlt
            ist. Liefert True, wenn tatsaechlich etwas geloescht wurde.
        EN: Deletes the selected rectangle, if one is selected. Returns
            True if something was actually deleted."""
        if self._ausgewaehlt is None:
            return False
        del self._rechtecke[self._ausgewaehlt]
        self._ausgewaehlt = None
        self.update()
        self.schwaerzungenGeaendert.emit()
        return True

    def alle_entfernen(self) -> None:
        if not self._rechtecke:
            return
        self._rechtecke = []
        self._ausgewaehlt = None
        self.update()
        self.schwaerzungenGeaendert.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.entferne_ausgewaehlte()
        else:
            super().keyPressEvent(event)

    # -- Zoom / Verschieben / zoom / pan -----------------------------------
    # DE: Identisch zu ZuschneidenCanvas -- siehe dort fuer Erklaerungen.
    # EN: Identical to ZuschneidenCanvas -- see there for explanations.

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

    # -- Koordinaten-Umrechnung / coordinate conversion --------------------

    def _zu_anteil(self, pos: QPointF) -> QPointF:
        r = self._bild_rect
        if r.width() <= 0 or r.height() <= 0:
            return QPointF(0, 0)
        return QPointF((pos.x() - r.left()) / r.width(), (pos.y() - r.top()) / r.height())

    def _zu_pixel_rect(self, rechteck: Rechteck) -> QRectF:
        r = self._bild_rect
        x0, y0, x1, y1 = rechteck
        return QRectF(r.left() + x0 * r.width(), r.top() + y0 * r.height(),
                      (x1 - x0) * r.width(), (y1 - y0) * r.height())

    # -- Zeichnen / painting ---------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#2b2b2b"))

        self._bild_rect = self._bild_rechteck()
        if self._pixmap is not None and not self._pixmap.isNull():
            painter.drawPixmap(self._bild_rect, self._pixmap, QRectF(self._pixmap.rect()))

        farbe = QColor(einstellungen.schwaerzungsfarbe())
        for i, rechteck in enumerate(self._rechtecke):
            pixel_rect = self._zu_pixel_rect(rechteck)
            painter.fillRect(pixel_rect, farbe)
            if i == self._ausgewaehlt:
                painter.setPen(QPen(QColor(46, 95, 163, 230), 2, Qt.PenStyle.SolidLine))
                painter.drawRect(pixel_rect)
                for ecke in (pixel_rect.topLeft(), pixel_rect.topRight(),
                            pixel_rect.bottomLeft(), pixel_rect.bottomRight()):
                    painter.fillRect(
                        QRectF(ecke.x() - _GRIFF_GROESSE / 2, ecke.y() - _GRIFF_GROESSE / 2,
                              _GRIFF_GROESSE, _GRIFF_GROESSE),
                        QColor(46, 95, 163, 255),
                    )

    # -- Maus / mouse --------------------------------------------------------

    def _ecke_bei(self, pos: QPointF) -> str | None:
        """DE: Liefert die Ecke ("tl"/"tr"/"bl"/"br") des ausgewaehlten
            Rechtecks, falls `pos` nahe genug an einem Eckgriff liegt.
        EN: Returns the corner ("tl"/"tr"/"bl"/"br") of the selected
            rectangle, if `pos` is close enough to a corner handle."""
        if self._ausgewaehlt is None:
            return None
        pixel_rect = self._zu_pixel_rect(self._rechtecke[self._ausgewaehlt])
        ecken = {
            "tl": pixel_rect.topLeft(), "tr": pixel_rect.topRight(),
            "bl": pixel_rect.bottomLeft(), "br": pixel_rect.bottomRight(),
        }
        for name, punkt in ecken.items():
            if (punkt - pos).manhattanLength() <= _GRIFF_TOLERANZ:
                return name
        return None

    def _rechteck_bei(self, pos: QPointF) -> int | None:
        """DE: Index des obersten (zuletzt gezeichneten) Rechtecks, das
            `pos` enthaelt, oder None.
        EN: Index of the topmost (most recently drawn) rectangle
            containing `pos`, or None."""
        for i in range(len(self._rechtecke) - 1, -1, -1):
            if self._zu_pixel_rect(self._rechtecke[i]).contains(pos):
                return i
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._bild_rect.isEmpty():
            return
        pos = event.position()

        ecke = self._ecke_bei(pos)
        if ecke is not None:
            self._ziehen = ecke
            self._ziehstart_bild = self._zu_anteil(pos)
            self._ziehstart_rechteck = self._rechtecke[self._ausgewaehlt]
            self.ziehenBegonnen.emit()
            return

        treffer = self._rechteck_bei(pos)
        if treffer is not None:
            self._ausgewaehlt = treffer
            self._ziehen = "verschieben"
            self._ziehstart_bild = self._zu_anteil(pos)
            self._ziehstart_rechteck = self._rechtecke[treffer]
            self.ziehenBegonnen.emit()
            self.update()
            return

        self._ausgewaehlt = None
        self._ziehen = "neu"
        self._ziehstart_bild = self._zu_anteil(pos)
        self._ziehstart_rechteck = (self._ziehstart_bild.x(), self._ziehstart_bild.y(),
                                    self._ziehstart_bild.x(), self._ziehstart_bild.y())
        self._rechtecke.append(self._ziehstart_rechteck)
        self._ausgewaehlt = len(self._rechtecke) - 1
        self.ziehenBegonnen.emit()
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._ziehen is None:
            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor if self._ecke_bei(event.position()) in ("tl", "br")
                else Qt.CursorShape.SizeBDiagCursor if self._ecke_bei(event.position()) in ("tr", "bl")
                else Qt.CursorShape.OpenHandCursor if self._rechteck_bei(event.position()) is not None
                else Qt.CursorShape.CrossCursor
            )
            return

        pos_anteil = self._zu_anteil(event.position())
        x0, y0, x1, y1 = self._ziehstart_rechteck

        if self._ziehen == "neu":
            neues = (min(self._ziehstart_bild.x(), pos_anteil.x()), min(self._ziehstart_bild.y(), pos_anteil.y()),
                    max(self._ziehstart_bild.x(), pos_anteil.x()), max(self._ziehstart_bild.y(), pos_anteil.y()))
        elif self._ziehen == "verschieben":
            dx = pos_anteil.x() - self._ziehstart_bild.x()
            dy = pos_anteil.y() - self._ziehstart_bild.y()
            breite, hoehe = x1 - x0, y1 - y0
            neu_x0 = max(0.0, min(1.0 - breite, x0 + dx))
            neu_y0 = max(0.0, min(1.0 - hoehe, y0 + dy))
            neues = (neu_x0, neu_y0, neu_x0 + breite, neu_y0 + hoehe)
        else:  # Ecke ziehen / dragging a corner
            neu_x0, neu_y0, neu_x1, neu_y1 = x0, y0, x1, y1
            if "l" in self._ziehen:
                neu_x0 = max(0.0, min(pos_anteil.x(), x1))
            if "r" in self._ziehen:
                neu_x1 = min(1.0, max(pos_anteil.x(), x0))
            if "t" in self._ziehen:
                neu_y0 = max(0.0, min(pos_anteil.y(), y1))
            if "b" in self._ziehen:
                neu_y1 = min(1.0, max(pos_anteil.y(), y0))
            neues = (neu_x0, neu_y0, neu_x1, neu_y1)

        self._rechtecke[self._ausgewaehlt] = neues
        self.update()
        self.schwaerzungenGeaendert.emit()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._ziehen is None:
            return
        if self._ziehen == "neu":
            x0, y0, x1, y1 = self._rechtecke[self._ausgewaehlt]
            if x1 - x0 < _MINDESTGROESSE or y1 - y0 < _MINDESTGROESSE:
                # DE: Nur ein Klick, kein echtes Rechteck -- verwerfen.
                # EN: Just a click, not a real rectangle -- discard.
                del self._rechtecke[self._ausgewaehlt]
                self._ausgewaehlt = None
                self.update()
        self._ziehen = None
        self._ziehstart_rechteck = None
