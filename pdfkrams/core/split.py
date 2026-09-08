"""
DE: Logik zum Zerschneiden einer Seite in mehrere Teile, waagerecht oder
    senkrecht. Die automatische Ausrichtung (Schnitt auf die ruhigste
    Bildspalte/-zeile in der Naehe der Sollposition legen) ist eine
    Portierung des Algorithmus aus dem urspruenglichen teilen.py-Skript,
    hier verallgemeinert auf beide Richtungen.

EN: Logic for cutting a page into multiple parts, horizontally or
    vertically. The automatic alignment (placing a cut on the quietest
    image column/row near the nominal position) is a port of the algorithm
    from the original teilen.py script, generalized here to both directions.
"""

from __future__ import annotations

from PIL import Image

from .document import SplitSpec

# DE: Verkleinerte Kantenlaenge, auf die fuer die Unruhe-Berechnung
#     herunterskaliert wird -- reicht fuer die Nahtsuche und ist schnell.
# EN: Downscaled edge length used for the "unruhe" (busyness) calculation --
#     enough for seam-finding and fast.
_ANALYSE_AUFLOESUNG = 600


def gleichmaessige_positionen(teile: int) -> list[float]:
    """DE: n-1 gleichmaessig verteilte Schnittpositionen fuer n Teile liefern.
    EN: Return n-1 evenly spaced cut positions for n parts."""
    if teile < 2:
        raise ValueError("Es muessen mindestens 2 Teile sein.")
    return [i / teile for i in range(1, teile)]


def _grenzen(positionen: list[float], dimension: int) -> list[int]:
    """DE: Sortierte Schnittpositionen (Anteile) in Pixelgrenzen inkl. Rand umrechnen.
    EN: Convert sorted cut positions (fractions) to pixel boundaries including the edges."""
    return [0] + [round(p * dimension) for p in sorted(positionen)] + [dimension]


def teile_bild(bild: Image.Image, spec: SplitSpec) -> list[Image.Image]:
    """
    DE: Bild anhand der senkrechten und waagerechten Schnittpositionen in ein
        Raster aus Teilbildern zerschneiden, in Leserichtung (zeilenweise
        von oben nach unten, innerhalb einer Zeile von links nach rechts).
        Ist nur eine Achse belegt, entsteht ein einfacher Streifen statt
        eines Rasters.

    EN: Cut an image into a grid of parts according to the vertical and
        horizontal cut positions, in reading order (row by row from top to
        bottom, left to right within a row). If only one axis has cuts, the
        result is a simple strip rather than a grid.
    """
    x_grenzen = _grenzen(spec.positionen_v, bild.width)
    y_grenzen = _grenzen(spec.positionen_h, bild.height)

    teile = []
    for y0, y1 in zip(y_grenzen, y_grenzen[1:]):
        for x0, x1 in zip(x_grenzen, x_grenzen[1:]):
            teile.append(bild.crop((x0, y0, x1, y1)))
    return teile


def _unruhe_werte(bild: Image.Image, vertikal: bool) -> list[float]:
    """DE: Pro Spalte (vertikal) bzw. Zeile (waagerecht) ein Unruhe-Mass
        liefern -- hohe Werte bedeuten viel Bildinhalt (z. B. Text), niedrige
        Werte einen ruhigen, moeglichst leeren Bereich, wie ihn eine
        Heftmitte oder ein Rand typischerweise hat.
    EN: Return a busyness measure per column (vertikal) resp. row
        (waagerecht) -- high values mean lots of image content (e.g. text),
        low values a quiet, mostly empty area, as a booklet's gutter or a
        margin typically is."""
    grau = bild.convert("L")
    breite, hoehe = grau.size
    lang = breite if vertikal else hoehe
    faktor = max(1, lang // _ANALYSE_AUFLOESUNG) if vertikal else max(1, breite // _ANALYSE_AUFLOESUNG)
    # DE: Nur die Achse verkleinern, entlang derer gemittelt wird -- die
    #     andere bleibt fuer eine genaue Positionsbestimmung in voller Aufloesung.
    # EN: Only downscale the axis being averaged over -- the other stays at
    #     full resolution for precise position finding.
    if vertikal:
        if faktor > 1:
            grau = grau.resize((breite, max(1, hoehe // faktor)), Image.BILINEAR)
        px = grau.load()
        b, h = grau.size
        return [sum(abs(px[x, y] - (sum(px[x, yy] for yy in range(h)) / h)) for y in range(h)) / h
                for x in range(b)]
    else:
        if faktor > 1:
            grau = grau.resize((max(1, breite // faktor), hoehe), Image.BILINEAR)
        px = grau.load()
        b, h = grau.size
        return [sum(abs(px[x, y] - (sum(px[xx, y] for xx in range(b)) / b)) for x in range(b)) / b
                for y in range(h)]


def _ruhigste_position(unruhe: list[float], nominal: int, fenster: int) -> int:
    """DE: Position mit dem niedrigsten Unruhe-Wert im Suchfenster um die Sollposition.
    EN: Position with the lowest busyness value within the search window around the nominal position."""
    a = max(0, nominal - fenster)
    b = min(len(unruhe) - 1, nominal + fenster)
    if b <= a:
        return nominal
    return min(range(a, b + 1), key=lambda x: unruhe[x])


def automatische_positionen(bild: Image.Image, richtung: str, teile: int,
                            fenster_prozent: float = 8.0) -> list[float]:
    """
    DE: Schnittpositionen wie bei gleichmaessige_positionen vorschlagen, sie
        aber jeweils auf die ruhigste Stelle in einem Suchfenster um die
        Sollposition ziehen. Gut geeignet, um Schnitte automatisch in eine
        Heftmitte oder einen leeren Rand statt mitten in Text zu legen.

    EN: Suggest cut positions like gleichmaessige_positionen, but pull each
        one to the quietest spot within a search window around the nominal
        position. Good for automatically placing cuts in a booklet's gutter
        or an empty margin instead of in the middle of text.
    """
    vertikal = richtung == "vertikal"
    dimension = bild.width if vertikal else bild.height
    nominal = [round(dimension * i / teile) for i in range(1, teile)]
    unruhe = _unruhe_werte(bild, vertikal)
    fenster = max(1, round(dimension / teile * fenster_prozent / 100))
    gefunden = [_ruhigste_position(unruhe, n, fenster) for n in nominal]
    return [p / dimension for p in gefunden]
