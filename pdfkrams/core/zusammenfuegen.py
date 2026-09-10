"""
DE: Logik zum Zusammenfuegen mehrerer Seiten/Bilder zu einer einzigen,
    grossen Seite -- das Gegenstueck zum Teilen-Werkzeug. Gedacht fuer
    grossformatige Vorlagen (z. B. A1-Schaltplaene), die in mehreren
    kleineren Teilen gescannt wurden. Jedes Teil (Kachel) hat eine eigene
    Position auf der gemeinsamen Leinwand, eine zusaetzliche
    Feinausrichtungs-Drehung (ueber die im Dreh-Werkzeug bereits gesetzte
    Drehung der Seite hinaus) und einstellbare Beschnittraender, um leicht
    unterschiedliche Scan-Raender bzw. bewusste Ueberlappung auszugleichen.

    Positionen/Groessen werden durchgehend in PDF-Punkten (1/72 Zoll)
    gerechnet, nicht in Pixeln -- so passen Teile mit unterschiedlicher
    nativer Aufloesung trotzdem physisch korrekt zusammen (wie beim Rest
    der App, siehe document.seitengroesse_pt).

EN: Logic for combining several pages/images into a single large page --
    the counterpart to the split tool. Meant for large-format originals
    (e.g. A1 schematics) that were scanned in several smaller parts. Each
    part (tile) has its own position on the shared canvas, an additional
    fine-alignment rotation (on top of whatever rotation the rotate tool
    already set for that page), and adjustable crop margins to compensate
    for slightly different scan edges resp. deliberate overlap.

    Positions/sizes are computed in PDF points (1/72 inch) throughout, not
    pixels -- so parts with different native resolutions still fit
    together physically correctly (like the rest of the app, see
    document.seitengroesse_pt).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PIL import Image

from .document import WorkingPage
from .rotate import rotiertes_bild
from .schwaerzung import schwaerzungen_anwenden

# DE: Maximaler Beschnitt je Rand, als Anteil der Kachelbreite/-hoehe --
#     verhindert, dass sich gegenueberliegende Raender ueberschneiden.
# EN: Maximum crop per edge, as a fraction of tile width/height -- prevents
#     opposite edges from overlapping each other.
_BESCHNITT_MAX = 0.45


@dataclass
class Kachel:
    """
    DE: Ein Teil im Zusammenfuegen-Werkzeug: Verweis auf seine Quellseite
        (per Index in der urspruenglich uebergebenen Seitenliste), Position
        der linken oberen Ecke auf der gemeinsamen Leinwand (in Punkten),
        zusaetzliche Feindrehung und Beschnitt je Rand (Anteil 0..0.45).

    EN: One part in the combine tool: reference to its source page (by
        index into the originally passed-in page list), position of its
        top-left corner on the shared canvas (in points), additional
        fine-alignment rotation, and crop per edge (fraction 0..0.45).
    """

    index: int
    rotation: float = 0.0
    x_pt: float = 0.0
    y_pt: float = 0.0
    beschnitt_links: float = 0.0
    beschnitt_rechts: float = 0.0
    beschnitt_oben: float = 0.0
    beschnitt_unten: float = 0.0


def kachel_bild(wp: WorkingPage, kachel: Kachel) -> tuple[Image.Image, float]:
    """
    DE: Die fertig gedrehte (Basisdrehung der Seite plus Feinausrichtung)
        und beschnittene Bilddarstellung einer Kachel liefern, zusammen
        mit ihrer tatsaechlichen DPI. Basisdrehung und Feindrehung werden
        in einem Schritt angewendet (ein Resampling statt zwei), fuer
        maximale Bildqualitaet.

    EN: Return a tile's fully rotated (page's base rotation plus fine
        alignment) and cropped image representation, together with its
        actual dpi. Base rotation and fine rotation are applied in one
        step (one resample instead of two), for maximum image quality.
    """
    # DE: Schwaerzung VOR dem Beschnitt auf das volle Kachelbild anwenden
    #     -- die Rechtecke sind als Anteile der GANZEN Quellseite
    #     definiert, nicht des beschnittenen Ergebnisses.
    # EN: Apply redaction to the full tile image before cropping -- the
    #     rectangles are defined as fractions of the ENTIRE source page,
    #     not of the cropped result.
    bild, dpi = rotiertes_bild(wp.source, wp.rotation + kachel.rotation, wp.spiegel_h, wp.spiegel_v)
    bild = schwaerzungen_anwenden(bild, wp.schwaerzungen)
    breite, hoehe = bild.size
    links = round(min(kachel.beschnitt_links, _BESCHNITT_MAX) * breite)
    rechts = round(min(kachel.beschnitt_rechts, _BESCHNITT_MAX) * breite)
    oben = round(min(kachel.beschnitt_oben, _BESCHNITT_MAX) * hoehe)
    unten = round(min(kachel.beschnitt_unten, _BESCHNITT_MAX) * hoehe)
    bild = bild.crop((links, oben, max(links + 1, breite - rechts), max(oben + 1, hoehe - unten)))
    return bild, dpi


def raster_anordnen(seiten: list[WorkingPage], spalten: int) -> list[Kachel]:
    """
    DE: Kacheln fuer alle `seiten` (in der gegebenen Reihenfolge) anlegen
        und in einem Zeilen/Spalten-Raster Kante an Kante anordnen --
        Zeilenhoehe/Spaltenbreite jeweils vom groessten Teil dieser Zeile/
        Spalte bestimmt. Nur ein Startpunkt: Position und Drehung jeder
        Kachel lassen sich danach frei anpassen.

    EN: Create tiles for all `seiten` (in the given order) and arrange
        them edge-to-edge in a row/column grid -- row height/column width
        each determined by that row's/column's largest tile. Just a
        starting point: each tile's position and rotation can be freely
        adjusted afterwards.
    """
    spalten = max(1, spalten)
    n = len(seiten)
    zeilen = (n + spalten - 1) // spalten if n else 0

    groessen_pt: list[tuple[float, float]] = []
    for wp in seiten:
        bild, dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
        groessen_pt.append((bild.width / dpi * 72.0, bild.height / dpi * 72.0))

    spaltenbreiten = [0.0] * spalten
    zeilenhoehen = [0.0] * zeilen
    for i, (breite_pt, hoehe_pt) in enumerate(groessen_pt):
        zeile, spalte = divmod(i, spalten)
        spaltenbreiten[spalte] = max(spaltenbreiten[spalte], breite_pt)
        zeilenhoehen[zeile] = max(zeilenhoehen[zeile], hoehe_pt)
    x_start = [sum(spaltenbreiten[:c]) for c in range(spalten)]
    y_start = [sum(zeilenhoehen[:r]) for r in range(zeilen)]

    kacheln = []
    for i in range(n):
        zeile, spalte = divmod(i, spalten)
        kacheln.append(Kachel(index=i, x_pt=x_start[spalte], y_pt=y_start[zeile]))
    return kacheln


def zusammengefuegtes_bild(
    seiten: list[WorkingPage], kacheln: list[Kachel],
    fortschritt: Callable[[int, int], None] | None = None,
) -> tuple[Image.Image, float]:
    """
    DE: Alle Kacheln gemaess ihrer Position zu einem einzigen Bild
        zusammensetzen. Kacheln mit niedrigerer nativer Aufloesung werden
        auf die hoechste beteiligte Aufloesung hochskaliert (nicht
        umgekehrt), damit keine bereits vorhandene Detailschaerfe verloren
        geht. Spaeter in `kacheln` stehende Teile werden ueber frueher
        eingesetzte gezeichnet (relevant nur bei bewusster Ueberlappung).
        Liefert (Bild, dpi). `fortschritt`, falls angegeben, wird nach
        jeder gerenderten Kachel mit (erledigt, gesamt) aufgerufen -- fuer
        eine Fortschrittsanzeige in der GUI.

    EN: Assemble all tiles into a single image according to their
        position. Tiles with lower native resolution are upscaled to the
        highest resolution involved (not the other way round), so no
        already-present detail is lost. Tiles listed later in `kacheln`
        are drawn over earlier ones (only relevant for deliberate
        overlap). Returns (image, dpi). `fortschritt`, if given, is
        called with (done, total) after each rendered tile -- for a
        progress display in the GUI.
    """
    if not kacheln:
        raise ValueError("Keine Kacheln zum Zusammenfuegen.")

    gerendert = []
    for i, k in enumerate(kacheln, start=1):
        gerendert.append((kachel_bild(seiten[k.index], k), k))
        if fortschritt is not None:
            fortschritt(i, len(kacheln))
    dpi_ziel = max(dpi for (_, dpi), _ in gerendert)
    skala = dpi_ziel / 72.0

    min_x = min(k.x_pt for _, k in gerendert)
    min_y = min(k.y_pt for _, k in gerendert)
    max_x = max(k.x_pt + bild.width / dpi * 72.0 for (bild, dpi), k in gerendert)
    max_y = max(k.y_pt + bild.height / dpi * 72.0 for (bild, dpi), k in gerendert)

    canvas_breite = max(1, round((max_x - min_x) * skala))
    canvas_hoehe = max(1, round((max_y - min_y) * skala))
    canvas = Image.new("RGB", (canvas_breite, canvas_hoehe), (255, 255, 255))

    for (bild, dpi), k in gerendert:
        if abs(dpi - dpi_ziel) > 1e-6:
            faktor = dpi_ziel / dpi
            neue_groesse = (max(1, round(bild.width * faktor)), max(1, round(bild.height * faktor)))
            bild = bild.resize(neue_groesse, Image.LANCZOS)
        x_px = round((k.x_pt - min_x) * skala)
        y_px = round((k.y_pt - min_y) * skala)
        canvas.paste(bild, (x_px, y_px))

    return canvas, dpi_ziel
