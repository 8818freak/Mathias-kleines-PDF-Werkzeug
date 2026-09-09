"""
DE: Seiten auf eine exakte physische Zielgroesse (DIN-A-Format oder
    freies Mass in mm) normieren -- Verallgemeinerung des urspruenglichen
    seitenmass.py-Skripts. Schwarze Scan-Raender (typisch, wenn die
    Vorlage kleiner als das Scannerglas ist) werden je Kante unabhaengig
    automatisch erkannt und abgeschnitten; danach wird die (ggf.
    beschnittene) Seite verlustarm auf die exakte Zielgroesse skaliert.
    Ohne erkennbaren Rand wird direkt skaliert.

EN: Normalize pages to an exact physical target size (DIN A format or a
    free size in mm) -- a generalization of the original seitenmass.py
    script. Black scan borders (typical when the original is smaller
    than the scanner bed) are automatically detected and cropped away,
    independently per edge; the (possibly cropped) page is then scaled
    to the exact target size. Without a detectable border, it's scaled
    directly.
"""

from __future__ import annotations

from PIL import Image

from .document import WorkingPage
from .rotate import rotiertes_bild

# DE: Die wichtigsten Papierformate weltweit -- (kurze Kante, lange
#     Kante) in mm, unabhaengig davon geschrieben, in welcher Masseinheit
#     sie ueblicherweise angegeben werden (US-Formate sind eigentlich in
#     Zoll definiert, hier aber wie alle anderen einheitlich in mm
#     hinterlegt -- die Anzeige in der gewaehlten Masseinheit passiert
#     erst in der Oberflaeche, siehe mm_zu_einheit()). Immer alle
#     Formate anbieten, unabhaengig von der eingestellten Masseinheit --
#     nur die ANGEZEIGTE Zahl richtet sich nach der Einheit, nicht die
#     Auswahl der Formate selbst.
# EN: The most important paper formats worldwide -- (short edge, long
#     edge) in mm, written uniformly regardless of which unit they are
#     conventionally specified in (US formats are technically defined in
#     inches, but stored here in mm like everything else -- display in
#     the chosen unit only happens in the UI, see mm_zu_einheit()).
#     Always offer every format regardless of the selected measurement
#     unit -- only the DISPLAYED number depends on the unit, not which
#     formats are available.
PAPIERFORMATE: dict[str, tuple[float, float]] = {
    "A0": (841.0, 1189.0),
    "A1": (594.0, 841.0),
    "A2": (420.0, 594.0),
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "A6": (105.0, 148.0),
    "US Letter": (215.9, 279.4),
    "US Legal": (215.9, 355.6),
    "US Executive": (184.15, 266.7),
    "US Tabloid/Ledger": (279.4, 431.8),
}

_MM_PRO_ZOLL = 25.4


def mm_zu_einheit(mm: float, einheit: str) -> float:
    """DE: Millimeter in die gewaehlte Anzeigeeinheit ("mm" oder "in") umrechnen.
    EN: Convert millimeters into the chosen display unit ("mm" or "in")."""
    return mm / _MM_PRO_ZOLL if einheit == "in" else mm


def einheit_zu_mm(wert: float, einheit: str) -> float:
    """DE: Einen in der gewaehlten Einheit ("mm" oder "in") angegebenen Wert nach mm umrechnen.
    EN: Convert a value given in the chosen unit ("mm" or "in") back to millimeters."""
    return wert * _MM_PRO_ZOLL if einheit == "in" else wert
# DE: Graustufe (0..255), unterhalb derer eine Zeile/Spalte im Mittel als
#     "schwarzer Rand" gilt.
# EN: Grayscale value (0..255) below which a row/column counts, on
#     average, as a "black border".
_SCHWARZ_SCHWELLE = 60
# DE: Hoechstens dieser Anteil einer Kante wird als Rand erkannt --
#     verhindert, dass bei generell dunklen Seiten zu viel abgeschnitten wird.
# EN: At most this fraction of an edge is recognized as a border --
#     prevents cropping too much on pages that are generally dark.
_MAX_RANDANTEIL = 0.2
# DE: Aufloesung, auf die fuer die Randerkennung herunterskaliert wird --
#     reicht fuer die Erkennung und ist schnell (wie split._ANALYSE_AUFLOESUNG).
# EN: Resolution the image is downscaled to for border detection -- enough
#     for detection and fast (like split._ANALYSE_AUFLOESUNG).
_ANALYSE_AUFLOESUNG = 300


def _lauflaenge(werte: list[float], schwelle: float, maximum: int) -> int:
    """DE: Anzahl aufeinanderfolgender Werte von vorne unterhalb der Schwelle, begrenzt auf `maximum`.
    EN: Number of consecutive values from the start below the threshold, capped at `maximum`."""
    n = 0
    for wert in werte:
        if wert >= schwelle or n >= maximum:
            break
        n += 1
    return n


def schwarzen_rand_erkennen(bild: Image.Image) -> tuple[float, float, float, float]:
    """
    DE: Liefert (links, oben, rechts, unten) als Anteil (0.._MAX_RANDANTEIL)
        der jeweiligen Kantenlaenge -- die Breite eines erkannten
        schwarzen Rands, 0.0 wenn an dieser Kante keiner erkennbar ist.

    EN: Returns (left, top, right, bottom) as a fraction
        (0.._MAX_RANDANTEIL) of the respective edge length -- the width
        of a detected black border, 0.0 if none is detectable on that edge.
    """
    grau = bild.convert("L")
    breite, hoehe = grau.size
    faktor = max(1, max(breite, hoehe) // _ANALYSE_AUFLOESUNG)
    if faktor > 1:
        grau = grau.resize((max(1, breite // faktor), max(1, hoehe // faktor)), Image.BILINEAR)
    b, h = grau.size
    px = grau.load()

    spalten_mittel = [sum(px[x, y] for y in range(h)) / h for x in range(b)]
    zeilen_mittel = [sum(px[x, y] for x in range(b)) / b for y in range(h)]

    max_x = round(b * _MAX_RANDANTEIL)
    max_y = round(h * _MAX_RANDANTEIL)
    links = _lauflaenge(spalten_mittel, _SCHWARZ_SCHWELLE, max_x) / b
    rechts = _lauflaenge(list(reversed(spalten_mittel)), _SCHWARZ_SCHWELLE, max_x) / b
    oben = _lauflaenge(zeilen_mittel, _SCHWARZ_SCHWELLE, max_y) / h
    unten = _lauflaenge(list(reversed(zeilen_mittel)), _SCHWARZ_SCHWELLE, max_y) / h
    return links, oben, rechts, unten


def aktuelle_groesse_mm(wp: WorkingPage, rand_abschneiden: bool = True) -> tuple[float, float]:
    """
    DE: Liefert die aktuelle physische Groesse der Seite in mm, ohne sie
        zu veraendern -- bei `rand_abschneiden=True` nach Abzug ihres
        erkannten schwarzen Rands (also die Groesse des eigentlichen
        Inhalts). Nuetzlich, um eine sinnvolle Zielgroesse zu waehlen.

    EN: Return the page's current physical size in mm, without changing
        it -- with `rand_abschneiden=True`, after subtracting its
        detected black border (i.e. the size of the actual content).
        Useful for picking a sensible target size.
    """
    bild, dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
    breite_px, hoehe_px = bild.size
    if rand_abschneiden:
        links, oben, rechts, unten = schwarzen_rand_erkennen(bild)
        breite_px = round(breite_px * (1 - links - rechts))
        hoehe_px = round(hoehe_px * (1 - oben - unten))
    return breite_px / dpi * _MM_PRO_ZOLL, hoehe_px / dpi * _MM_PRO_ZOLL


def naheliegendes_format(breite_mm: float, hoehe_mm: float, toleranz: float = 0.05) -> str | None:
    """
    DE: Liefert den Namen des Papierformats (DIN oder US), dessen Masse
        (in passender Ausrichtung) am naechsten an (breite_mm, hoehe_mm)
        liegen, wenn die Abweichung in beiden Richtungen innerhalb
        `toleranz` liegt -- sonst None (kein Format passt gut genug).

    EN: Return the name of the paper format (DIN or US) whose dimensions
        (in the matching orientation) come closest to (breite_mm,
        hoehe_mm), if the deviation in both directions is within
        `toleranz` -- otherwise None (no format fits well enough).
    """
    kurz, lang = min(breite_mm, hoehe_mm), max(breite_mm, hoehe_mm)
    beste: str | None = None
    beste_abweichung = None
    for name, (k, l) in PAPIERFORMATE.items():
        abweichung = max(abs(kurz - k) / k, abs(lang - l) / l)
        if abweichung <= toleranz and (beste_abweichung is None or abweichung < beste_abweichung):
            beste = name
            beste_abweichung = abweichung
    return beste


def seite_normieren(wp: WorkingPage, ziel_breite_mm: float, ziel_hoehe_mm: float,
                    dpi: float, rand_abschneiden: bool = True) -> tuple[Image.Image, float]:
    """
    DE: Seite rendern, optional ihren schwarzen Rand abschneiden und auf
        exakt (ziel_breite_mm x ziel_hoehe_mm) bei `dpi` skalieren. Die
        Zielmasse werden automatisch an die Ausrichtung der Seite
        angepasst (Hochformat-Ziel auf eine Querformat-Seite wird
        entsprechend gedreht interpretiert, nicht die Seite selbst
        gedreht). Liefert (Bild, dpi).

    EN: Render the page, optionally crop its black border, and scale to
        exactly (ziel_breite_mm x ziel_hoehe_mm) at `dpi`. The target
        dimensions are automatically adapted to the page's orientation
        (a portrait target on a landscape page is interpreted rotated,
        without rotating the page itself). Returns (image, dpi).
    """
    bild, _dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)

    if (bild.width > bild.height) != (ziel_breite_mm > ziel_hoehe_mm):
        ziel_breite_mm, ziel_hoehe_mm = ziel_hoehe_mm, ziel_breite_mm

    if rand_abschneiden:
        links, oben, rechts, unten = schwarzen_rand_erkennen(bild)
        breite, hoehe = bild.size
        box = (
            round(links * breite), round(oben * hoehe),
            breite - round(rechts * breite), hoehe - round(unten * hoehe),
        )
        if box[2] > box[0] and box[3] > box[1]:
            bild = bild.crop(box)

    ziel_px_breite = max(1, round(ziel_breite_mm / _MM_PRO_ZOLL * dpi))
    ziel_px_hoehe = max(1, round(ziel_hoehe_mm / _MM_PRO_ZOLL * dpi))
    if bild.size != (ziel_px_breite, ziel_px_hoehe):
        bild = bild.resize((ziel_px_breite, ziel_px_hoehe), Image.LANCZOS)

    return bild, dpi
