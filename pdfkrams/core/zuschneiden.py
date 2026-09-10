"""
DE: Seiten von allen vier Raendern aus manuell zuschneiden -- anders als
    "Seitenmaß normieren" (das auf eine ZIELGROESSE skaliert und dabei
    hoechstens einen automatisch erkannten schwarzen Rand abschneidet)
    schneidet dieses Werkzeug genau die vom Nutzer angegebenen physischen
    Randmasse ab, ohne zu skalieren -- z. B. um Lochrandstreifen, einen
    Heftrand oder ungewollten Seiteninhalt praezise zu entfernen. Die
    Aufloesung (dpi) der Seite bleibt dabei unveraendert.

EN: Manually crop pages from all four edges -- unlike "Normalize page
    size" (which scales to a TARGET size and, at most, crops an
    automatically detected black border) this tool cuts away exactly the
    physical margins the user specifies, without scaling -- e.g. to
    precisely remove punch-hole strips, a binding margin, or unwanted
    page content. The page's resolution (dpi) stays unchanged.
"""

from __future__ import annotations

from PIL import Image

from .document import WorkingPage
from .rotate import rotiertes_bild
from .schwaerzung import schwaerzungen_anwenden

_MM_PRO_ZOLL = 25.4


def seite_zuschneiden(
    wp: WorkingPage, links_mm: float, oben_mm: float, rechts_mm: float, unten_mm: float,
) -> tuple[Image.Image, float]:
    """
    DE: Seite rendern und die angegebenen Randmasse (in mm) von jeder
        Kante abschneiden, ohne zu skalieren. Liefert (Bild, dpi). Die
        Randmasse werden defensiv auf die tatsaechliche Seitengroesse
        begrenzt (mindestens 1 Pixel Ergebnis je Achse bleibt immer
        erhalten) -- so kann dieselbe feste Randangabe unbesorgt auf
        mehrere, nicht ganz gleich grosse Seiten angewendet werden.

    EN: Render the page and cut away the given margins (in mm) from each
        edge, without scaling. Returns (image, dpi). The margins are
        defensively clamped to the page's actual size (at least 1 pixel
        of result remains per axis) -- so the same fixed margins can
        safely be applied to several pages that aren't all exactly the
        same size.
    """
    # DE: Schwaerzung VOR dem Beschnitt anwenden -- die Rechtecke sind
    #     als Anteile der urspruenglichen (unbeschnittenen) Seite definiert.
    # EN: Apply redaction before cropping -- the rectangles are defined
    #     as fractions of the original (uncropped) page.
    bild, dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
    bild = schwaerzungen_anwenden(bild, wp.schwaerzungen)
    breite_px, hoehe_px = bild.size
    px_pro_mm = dpi / _MM_PRO_ZOLL

    x0 = round(links_mm * px_pro_mm)
    y0 = round(oben_mm * px_pro_mm)
    x1 = breite_px - round(rechts_mm * px_pro_mm)
    y1 = hoehe_px - round(unten_mm * px_pro_mm)

    x0 = max(0, min(x0, breite_px - 1))
    y0 = max(0, min(y0, hoehe_px - 1))
    x1 = max(x0 + 1, min(x1, breite_px))
    y1 = max(y0 + 1, min(y1, hoehe_px))

    return bild.crop((x0, y0, x1, y1)), dpi
