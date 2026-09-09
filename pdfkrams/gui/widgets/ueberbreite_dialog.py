"""
DE: Dialog fuer das Heftseiten-Werkzeug, wenn ein ausgewaehlter Scan
    deutlich breiter ist als die uebrigen -- typischerweise ein Umschlag
    oder eine Seite mit Aufklappteil, oft mit mehreren eigenstaendigen
    Seiten (Ruecktitel, Adressliste, Vortitel, Klappe, …) in einem Bild.
    Statt eine feste Aufteilung zu erraten, bekommt der Nutzer denselben
    Ziehen-Editor wie im Teilen-Werkzeug (inkl. Zoom): beliebig viele
    Schnittlinien frei per Maus platzieren, damit die Aufteilung garantiert
    stimmt.

    Die Sattelheft-Formel weiss bereits, auf welche zwei Seitenzahlen des
    fertigen Dokuments dieses eine Scan-Blatt gehoert (z. B. Seite 1 und
    Seite 20) -- sie weiss nur nicht, welche der geschnittenen Teile zu
    welcher der beiden Seiten gehoeren. Deshalb wird zusaetzlich erfragt,
    wo die Grenze zwischen den beiden Haelften liegt: die Teile links davon
    gehen an die eine Zielseite, die Teile rechts davon an die andere. Damit
    ist die Einsortierung wieder vollautomatisch, nur die Zuordnung selbst
    muss der Nutzer angeben, weil sie sich aus dem Bildinhalt nicht
    herleiten laesst.

EN: Dialog for the booklet tool when a selected scan is clearly wider than
    the others -- typically a cover or a page with a foldout part, often
    containing several independent pages (back title, address list, front
    title, flap, …) in one image. Instead of guessing a fixed split, the
    user gets the same drag editor as in the split tool (including zoom):
    place as many cut lines as needed freely with the mouse, so the split
    is guaranteed correct.

    The saddle-stitch formula already knows which two page numbers of the
    finished document this one scan sheet belongs to (e.g. page 1 and page
    20) -- it just doesn't know which of the cut parts belong to which of
    the two pages. So the dialog additionally asks where the boundary
    between the two halves lies: parts to its left go to one target page,
    parts to its right go to the other. That makes the placement fully
    automatic again -- only the assignment itself needs the user's input,
    since it can't be derived from the image content.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.split import gleichmaessige_positionen
from pdfkrams.gui.widgets.split_canvas import SplitCanvas


class _UeberbreiteDialog(QDialog):
    def __init__(self, pixmap, bezeichnung: str, vorschlag_teile: int,
                west_seite: int, ost_seite: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Überbreite Seite teilen"))
        self.resize(900, 760)
        self._west_seite = west_seite
        self._ost_seite = ost_seite

        hinweis = QLabel(
            self.tr("„{0}“ ist deutlich breiter als die übrigen ausgewählten Seiten. "
                   "Gelbe Linien mit der Maus so verschieben, dass jede der einzelnen Seiten "
                   "(Umschlagteile, Aufklappteil, …) für sich getrennt wird -- mit Strg/Cmd+"
                   "Scrollen bzw. Pinch-Geste vergrößern für genaues Treffen.").format(bezeichnung)
        )
        hinweis.setWordWrap(True)

        self._pixmap = pixmap
        self._canvas = SplitCanvas()
        self._canvas.seite_setzen(pixmap, gleichmaessige_positionen(max(2, vorschlag_teile)), [])

        steuerung = QHBoxLayout()
        self._teile_feld = QSpinBox()
        self._teile_feld.setRange(1, 20)
        self._teile_feld.setValue(max(2, vorschlag_teile))
        self._teile_feld.setPrefix(self.tr("Teile: "))
        self._teile_feld.valueChanged.connect(self._teile_geaendert)
        btn_gleichmaessig = QPushButton(self.tr("Gleichmäßig verteilen"))
        btn_gleichmaessig.clicked.connect(self._gleichmaessig_verteilen)

        btn_zoom_aus = QPushButton("−")
        btn_zoom_aus.setFixedWidth(32)
        btn_zoom_aus.clicked.connect(lambda: self._canvas.zoom_schritt(1 / 1.4))
        self._zoom_label = QLabel(self.tr("100 %"))
        self._zoom_label.setFixedWidth(56)
        btn_zoom_ein = QPushButton("+")
        btn_zoom_ein.setFixedWidth(32)
        btn_zoom_ein.clicked.connect(lambda: self._canvas.zoom_schritt(1.4))
        btn_einpassen = QPushButton(self.tr("Einpassen"))
        btn_einpassen.clicked.connect(self._canvas.einpassen)
        self._canvas.zoomGeaendert.connect(lambda z: self._zoom_label.setText(self.tr("{0} %").format(round(z * 100))))

        steuerung.addWidget(self._teile_feld)
        steuerung.addWidget(btn_gleichmaessig)
        steuerung.addStretch(1)
        steuerung.addWidget(btn_zoom_aus)
        steuerung.addWidget(self._zoom_label)
        steuerung.addWidget(btn_zoom_ein)
        steuerung.addWidget(btn_einpassen)

        # DE: Zuordnung der Teile zu den beiden Zielseiten im Dokument.
        # EN: Assignment of the parts to the two target pages in the document.
        self._grenze_hinweis = QLabel()
        self._grenze_hinweis.setWordWrap(True)
        self._grenze_feld = QSpinBox()
        self._grenze_feld.setRange(0, self._teile_feld.value())
        self._grenze_feld.setValue(self._teile_feld.value() // 2)
        self._grenze_feld.valueChanged.connect(self._grenze_aktualisieren)
        grenze_zeile = QHBoxLayout()
        grenze_zeile.addWidget(QLabel(self.tr("Grenze nach Teil:")))
        grenze_zeile.addWidget(self._grenze_feld)
        grenze_zeile.addStretch(1)

        knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        knoepfe.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addLayout(steuerung)
        layout.addWidget(self._canvas, 1)
        layout.addWidget(self._grenze_hinweis)
        layout.addLayout(grenze_zeile)
        layout.addWidget(knoepfe)

        self._grenze_aktualisieren()

    def _gleichmaessig_verteilen(self) -> None:
        neue_pos_v = gleichmaessige_positionen(self._teile_feld.value())
        self._canvas.seite_setzen(self._pixmap, neue_pos_v, [])

    def _teile_geaendert(self, teile: int) -> None:
        self._grenze_feld.setMaximum(teile)
        self._grenze_aktualisieren()

    def _grenze_aktualisieren(self) -> None:
        n = self._teile_feld.value()
        k = self._grenze_feld.value()
        links = (
            self.tr("Teil 1–{0}").format(k) if k > 1
            else (self.tr("Teil 1") if k == 1 else self.tr("(keine)"))
        )
        rechts = (
            self.tr("Teil {0}–{1}").format(k + 1, n) if k + 1 < n
            else (self.tr("Teil {0}").format(n) if k + 1 == n else self.tr("(keine)"))
        )
        self._grenze_hinweis.setText(
            self.tr("{0} → Seite {1} im fertigen Dokument.  {2} → Seite {3} im fertigen Dokument.").format(
                links, self._west_seite, rechts, self._ost_seite
            )
        )

    def positionen(self) -> list[float]:
        pos_v, _pos_h = self._canvas.positionen()
        return sorted(pos_v)

    def grenze(self) -> int:
        return self._grenze_feld.value()


def ueberbreite_seite_teilen_abfragen(
    parent: QWidget, pixmap, bezeichnung: str, vorschlag_teile: int,
    west_seite: int, ost_seite: int,
) -> tuple[list[float], int]:
    """
    DE: Zeigt den Ziehen-Editor fuer eine ueberbreite Seite und liefert
        (Schnittpositionen, Grenze) -- die senkrechten Schnittpositionen
        (Anteile 0..1, sortiert) und die Anzahl Teile von links, die zur
        "West"-Zielseite gehoeren (die uebrigen gehoeren zur "Ost"-Seite).
        Kein Abbrechen moeglich (nur OK) -- eine Entscheidung ist noetig,
        um mit der Verarbeitung fortzufahren.

    EN: Shows the drag editor for an overwide page and returns
        (cut positions, boundary) -- the vertical cut positions (fractions
        0..1, sorted) and the number of parts from the left that belong to
        the "west" target page (the rest belong to the "ost" page). No
        cancel option (OK only) -- a decision is needed to continue
        processing.
    """
    dialog = _UeberbreiteDialog(pixmap, bezeichnung, vorschlag_teile, west_seite, ost_seite, parent)
    dialog.exec()
    return dialog.positionen(), dialog.grenze()
