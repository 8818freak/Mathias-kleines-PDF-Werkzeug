"""
DE: Schwaerzen (Redaction) -- brennt deckend schwarze Rechtecke dauerhaft
    in die Bildpixel einer Seite ein, statt sie nur optisch zu ueberdecken.
    Das ist der entscheidende Unterschied zu einem einfachen schwarzen
    Kasten auf einer unveraenderten PDF-Seite: liesse man die Original-
    Vektorseite (Text/Grafik) im PDF bestehen und legte nur eine schwarze
    Flaeche DARUEBER, waere der darunterliegende Text weiterhin markier-
    und kopierbar bzw. durch simples Entfernen der Flaeche wieder
    sichtbar -- ein haeufiger, ernsthafter Fehler bei "Schwaerzungen" in
    echten Aktensystemen. Deshalb erzwingen alle Exportpfade (siehe
    combine.py, komprimierung.py) fuer Seiten mit Schwaerzungen die
    Rasterung (keine Vektor-Passthrough-Abkuerzung mehr) und brennen die
    Rechtecke danach in genau dieses Rasterbild ein -- was am Ende in der
    PDF landet, ist ein reines Bild ohne darunterliegenden Text/Vektor-
    inhalt in den geschwaerzten Bereichen.

EN: Redaction -- permanently burns fully opaque black rectangles into a
    page's image pixels, instead of merely visually covering them. This
    is the crucial difference from a plain black box on an otherwise
    unmodified PDF page: leaving the original vector page (text/graphics)
    intact in the PDF and placing only a black shape ON TOP of it would
    leave the underlying text still selectable/copyable, resp. visible
    again by simply removing the shape -- a common, serious mistake in
    real-world "redaction" of case files. That's why every export path
    (see combine.py, komprimierung.py) forces rasterization (no more
    vector-passthrough shortcut) for pages with redactions, and only then
    burns the rectangles into that very raster image -- what ends up in
    the PDF is a plain image with no underlying text/vector content left
    in the redacted areas.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

# DE: Global verwendete Schwaerzungsfarbe -- deckend, keine Transparenz
#     (siehe Moduldocstring, warum "deckend" hier sicherheitsrelevant
#     ist). Standard Schwarz, wie in Akten/Verwaltungsschriftgut ueblich;
#     ueber pdfkrams.einstellungen (Praeferenzen-Dialog) umstellbar --
#     dieses Modul selbst bleibt bewusst Qt-frei, siehe farbe_setzen().
# EN: Globally used redaction color -- fully opaque, no transparency
#     (see module docstring for why "opaque" is safety-relevant here).
#     Defaults to black, as customary in case files/administrative
#     records; adjustable via pdfkrams.einstellungen (Preferences
#     dialog) -- this module itself deliberately stays Qt-free, see
#     farbe_setzen().
STANDARDFARBE = (0, 0, 0)
_aktuelle_farbe: tuple[int, int, int] = STANDARDFARBE


def farbe_setzen(rgb: tuple[int, int, int]) -> None:
    """DE: Legt die global verwendete Schwaerzungsfarbe fest (siehe
        schwaerzungen_anwenden). Wird von pdfkrams.einstellungen bei
        Programmstart und bei jeder Aenderung der Praeferenz aufgerufen.
    EN: Sets the globally used redaction color (see
        schwaerzungen_anwenden). Called by pdfkrams.einstellungen on
        startup and whenever the preference changes."""
    global _aktuelle_farbe
    _aktuelle_farbe = rgb


def farbe() -> tuple[int, int, int]:
    return _aktuelle_farbe


def schwaerzungen_anwenden(
    bild: Image.Image, schwaerzungen: list[tuple[float, float, float, float]],
    farbe: tuple[int, int, int] | None = None,
) -> Image.Image:
    """
    DE: Zeichnet jedes Schwaerzungs-Rechteck (x0, y0, x1, y1 als Anteile
        0..1 von `bild`) deckend in `farbe` (Standard: die aktuell
        eingestellte globale Schwaerzungsfarbe, siehe farbe_setzen()) in
        eine Kopie von `bild` ein. Leere Liste liefert `bild` unveraendert
        zurueck (dieselbe Referenz, keine unnoetige Kopie).
    EN: Draws every redaction rectangle (x0, y0, x1, y1 as fractions 0..1
        of `bild`) fully opaque in `farbe` (default: the currently
        configured global redaction color, see farbe_setzen()) into a
        copy of `bild`. An empty list returns `bild` unchanged (the same
        reference, no needless copy).
    """
    if not schwaerzungen:
        return bild
    ziel_farbe = farbe if farbe is not None else _aktuelle_farbe
    ergebnis = bild.copy()
    zeichner = ImageDraw.Draw(ergebnis)
    breite, hoehe = ergebnis.size
    for x0, y0, x1, y1 in schwaerzungen:
        kasten = (round(x0 * breite), round(y0 * hoehe), round(x1 * breite), round(y1 * hoehe))
        zeichner.rectangle(kasten, fill=ziel_farbe)
    return ergebnis
