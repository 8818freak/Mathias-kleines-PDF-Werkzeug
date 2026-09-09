"""
DE: Logik zum Drehen (beliebiger Winkel, im Uhrzeigersinn) und Spiegeln
    einer einzelnen Seite. Winkelkonvention im ganzen Programm: positive
    Grad = im Uhrzeigersinn, so wie es beim Betrachten einer Seite auch
    intuitiv erwartet wird und wie es auch die PDF-Spezifikation fuer den
    /Rotate-Eintrag einer Seite festlegt.

EN: Logic for rotating (arbitrary angle, clockwise) and mirroring a single
    page. Angle convention used throughout the program: positive degrees
    means clockwise, matching both the intuitive expectation when looking
    at a page and the PDF specification's /Rotate page entry.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

import pymupdf as fitz  # PyMuPDF (neuer Modulname / new module name)

from .document import PageSource, STANDARD_DPI, bild_dpi

# DE: Toleranz, innerhalb derer ein Winkel als rechter Winkel (0/90/180/270)
#     gilt -- wichtig, um den verlustfreien PDF-Pfad in combine.py zu treffen.
# EN: Tolerance within which an angle counts as a right angle (0/90/180/270)
#     -- important to hit the lossless PDF path in combine.py.
_WINKEL_TOLERANZ = 1e-6


def normalisiert(grad: float) -> float:
    """DE: Winkel auf den Bereich (-180, 180] bringen.
    EN: Normalize an angle to the range (-180, 180]."""
    g = grad % 360.0
    if g > 180.0:
        g -= 360.0
    return g


def ist_rechter_winkel(grad: float) -> bool:
    """DE: Prueft, ob der (normalisierte) Winkel 0, 90, 180 oder -90 ist.
    EN: Checks whether the (normalized) angle is 0, 90, 180, or -90."""
    g = normalisiert(grad)
    return any(abs(g - ziel) < _WINKEL_TOLERANZ for ziel in (0.0, 90.0, 180.0, -90.0))


def bild_transformieren(bild: Image.Image, winkel_grad: float, spiegel_h: bool, spiegel_v: bool) -> Image.Image:
    """
    DE: Spiegelung und Drehung auf ein bereits geladenes Bild anwenden.
        Reihenfolge ist immer: erst spiegeln, dann drehen. Rand, der durch
        die Drehung entsteht, wird weiss aufgefuellt.

    EN: Apply mirroring and rotation to an already-loaded image. Order is
        always: mirror first, then rotate. Any border created by the
        rotation is filled white.
    """
    if spiegel_h:
        bild = bild.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if spiegel_v:
        bild = bild.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if winkel_grad:
        # DE: PIL dreht bei positivem Winkel gegen den Uhrzeigersinn, daher
        #     hier das Vorzeichen umdrehen, um unsere Konvention (im
        #     Uhrzeigersinn) einzuhalten. Rechte Winkel behandelt PIL intern
        #     verlustfrei (kein Resampling), andere Winkel werden interpoliert.
        # EN: PIL rotates counter-clockwise for a positive angle, so the
        #     sign is flipped here to keep our clockwise convention. PIL
        #     handles right angles losslessly internally (no resampling),
        #     other angles are interpolated.
        bild = bild.rotate(-winkel_grad, resample=Image.Resampling.BICUBIC,
                           expand=True, fillcolor=(255, 255, 255))
    return bild


def _native_dpi_gescannter_seite(page: fitz.Page) -> float | None:
    """
    DE: Fuer eine PDF-Seite, die (ggf. unter anderem) ein oder mehrere
        seitenfuellende Scan-Bilder enthaelt, deren native Aufloesung
        liefern. Manche Scan-PDFs legen zwei nahezu identische Bilder
        uebereinander auf dieselbe Position (z. B. eine JPEG2000-Version
        und eine zusaetzliche mit Alpha-Maske) -- hier wird ueber alle
        Bilder gegangen, die die Seite zu mindestens 90% abdecken, und die
        hoechste sich daraus ergebende Aufloesung genommen, damit kein
        echter Detailgehalt verloren geht. Liefert None, wenn kein
        seitenfuellendes Bild existiert (z. B. echter Vektorinhalt) -- dann
        gibt es keine sinnvolle native Aufloesung, an der man sich
        orientieren koennte.

    EN: For a PDF page that contains one or more page-filling scanned
        images (possibly among other content), return their native
        resolution. Some scan PDFs stack two near-identical images at the
        same position (e.g. a JPEG2000 version plus an extra one with an
        alpha mask) -- this looks at every image covering at least 90% of
        the page and takes the highest resulting resolution, so no real
        detail is lost. Returns None if no page-filling image exists (e.g.
        genuine vector content) -- in that case there's no meaningful
        native resolution to go by.
    """
    seitenflaeche = page.rect.width * page.rect.height
    if seitenflaeche <= 0:
        return None
    hoechste_dpi = None
    for eintrag in page.get_image_info(xrefs=True):
        bbox = eintrag["bbox"]
        breite_pt, hoehe_pt = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if breite_pt <= 0 or hoehe_pt <= 0:
            continue
        if (breite_pt * hoehe_pt) / seitenflaeche < 0.9:
            continue  # DE: kein seitenfuellendes Bild / EN: not a page-filling image
        dpi = eintrag["width"] / breite_pt * 72.0
        if hoechste_dpi is None or dpi > hoechste_dpi:
            hoechste_dpi = dpi
    return hoechste_dpi


def rotiertes_bild(source: PageSource, winkel_grad: float, spiegel_h: bool, spiegel_v: bool,
                    dpi: float = STANDARD_DPI) -> tuple[Image.Image, float]:
    """
    DE: Seite in voller Qualitaet rastern und Spiegelung/Drehung darauf
        anwenden. Liefert (Bild, tatsaechlich verwendete DPI) -- bei Bildern
        wird deren eigene Aufloesung verwendet, nicht der dpi-Parameter. Bei
        PDF-Seiten, die aus einem einzigen seitenfuellenden Scan-Bild
        bestehen, wird `dpi` zusaetzlich auf die native Aufloesung dieses
        Bildes begrenzt -- sonst wuerde ein z. B. mit 150 dpi gescanntes
        Blatt beim Rastern erst kuenstlich auf 300 dpi hochgerechnet
        (Interpolation ohne echten Informationsgewinn), was nachfolgende
        Schritte wie eine JPEG-Verkleinerung unnoetig aufblaeht statt sie
        kleiner zu machen.

    EN: Rasterize the page at full quality and apply mirroring/rotation.
        Returns (image, dpi actually used) -- for images their own
        resolution is used rather than the dpi parameter. For PDF pages
        that consist of a single page-filling scanned image, `dpi` is
        additionally capped at that image's native resolution -- otherwise
        e.g. a sheet scanned at 150 dpi would be artificially upscaled to
        300 dpi during rasterization (interpolation with no real
        information gain), which needlessly bloats downstream steps like
        JPEG shrinking instead of making them smaller.
    """
    if source.kind == "pdf":
        with fitz.open(source.path) as doc:
            page = doc[source.index]
            nativ = _native_dpi_gescannter_seite(page)
            effektive_dpi = min(dpi, nativ) if nativ else dpi
            skala = effektive_dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(skala, skala), colorspace=fitz.csRGB, alpha=False)
            bild = Image.frombytes("RGB", (pix.width, pix.height), bytes(pix.samples))
            dpi = effektive_dpi
    else:
        with Image.open(source.path) as im:
            im.seek(source.index)
            bild = im.convert("RGB")
            dpi_x, _ = bild_dpi(im)
            dpi = dpi_x

    return bild_transformieren(bild, winkel_grad, spiegel_h, spiegel_v), dpi


# DE: Suchbereich (+/- Grad) und Schrittweiten fuer die Schraeglagenerkennung
#     -- grob zuerst ueber den ganzen Bereich, dann fein um den besten groben
#     Treffer herum, statt gleich alles fein abzusuchen (deutlich schneller,
#     bei kaum schlechterer Genauigkeit).
# EN: Search range (+/- degrees) and step sizes for skew detection -- coarse
#     first across the whole range, then fine around the best coarse hit,
#     instead of searching everything at fine resolution right away (much
#     faster, at barely worse accuracy).
_SCHRAEGLAGE_SUCHBEREICH = 8.0
_SCHRAEGLAGE_GROB_SCHRITT = 0.5
_SCHRAEGLAGE_FEIN_BEREICH = 0.6
_SCHRAEGLAGE_FEIN_SCHRITT = 0.05
# DE: Laengere Kante in Pixeln, auf die fuer die Analyse herunterskaliert
#     wird -- reicht fuer zuverlaessige Zeilenerkennung und ist schnell.
# EN: Longer edge in pixels the image is downscaled to for analysis --
#     enough for reliable line detection and fast.
_SCHRAEGLAGE_ANALYSE_AUFLOESUNG = 700
# DE: Graustufe (0..255), unterhalb derer ein Pixel als "Tinte" (Text/
#     Linie) statt Hintergrund gilt.
# EN: Grayscale value (0..255) below which a pixel counts as "ink" (text/
#     line) rather than background.
_SCHRAEGLAGE_TINTE_SCHWELLE = 150
# DE: Mindestverhaeltnis von bester zu mittlerer Profil-Varianz, damit ein
#     Treffer als zuverlaessig genug fuer einen Vorschlag gilt -- verhindert
#     einen Vorschlag "aus dem Rauschen" bei Seiten ohne klare horizontale
#     Struktur (Fotos, grafiklastige Seiten).
# EN: Minimum ratio of best to mean profile variance for a hit to count as
#     reliable enough to suggest -- prevents a suggestion "from the noise"
#     on pages without clear horizontal structure (photos, graphics-heavy
#     pages).
_SCHRAEGLAGE_MINDEST_VERHAELTNIS = 1.15


def _projektionsprofil_varianz(tinte: np.ndarray, pil_winkel_grad: float) -> float:
    """DE: Tinte-Maske um pil_winkel_grad drehen (PIL-Konvention, gegen den
        Uhrzeigersinn) und die Varianz der zeilenweisen Pixel-Summen
        liefern -- hoeher, je schaerfer sich Textzeilen zu horizontalen
        Baendern verdichten.
    EN: Rotate the ink mask by pil_winkel_grad (PIL convention, counter-
        clockwise) and return the variance of the row-wise pixel sums --
        higher the more sharply text lines condense into horizontal
        bands."""
    gedreht = Image.fromarray(tinte).rotate(
        pil_winkel_grad, resample=Image.Resampling.BILINEAR, expand=False, fillcolor=0,
    )
    zeilen_summen = np.asarray(gedreht, dtype=np.float64).sum(axis=1)
    return float(zeilen_summen.var())


def schraeglagen_korrektur_erkennen(bild: Image.Image) -> float | None:
    """
    DE: Erkennt per Projektionsprofil-Analyse (Textzeilen zu horizontalen
        Baendern verdichten), um wie viel Grad `bild` zusaetzlich gedreht
        werden muesste, um gerade zu stehen -- als Korrektur in der
        Winkelkonvention der App (positiv = im Uhrzeigersinn), die auf
        die schon in `bild` enthaltene Drehung AUFADDIERT werden soll.
        Liefert None, wenn kein hinreichend deutliches horizontales
        Zeilenmuster gefunden wurde (z. B. Fotos oder grafiklastige
        Seiten ohne klaren Text) -- dann sollte kein automatischer
        Vorschlag gemacht werden, statt eine wahrscheinlich falsche Zahl
        anzuzeigen.

    EN: Detects, via projection-profile analysis (condensing text lines
        into horizontal bands), how many additional degrees `bild` would
        need to be rotated to stand straight -- as a correction in the
        app's angle convention (positive = clockwise), meant to be ADDED
        to whatever rotation `bild` already reflects. Returns None if no
        sufficiently clear horizontal line pattern was found (e.g. photos
        or graphics-heavy pages without clear text) -- in that case, no
        automatic suggestion should be made rather than showing a
        probably-wrong number.
    """
    grau = bild.convert("L")
    breite, hoehe = grau.size
    faktor = max(1, max(breite, hoehe) // _SCHRAEGLAGE_ANALYSE_AUFLOESUNG)
    if faktor > 1:
        grau = grau.resize((max(1, breite // faktor), max(1, hoehe // faktor)), Image.BILINEAR)
    tinte = (np.asarray(grau, dtype=np.uint8) < _SCHRAEGLAGE_TINTE_SCHWELLE).astype(np.uint8) * 255

    grob_kandidaten = np.arange(
        -_SCHRAEGLAGE_SUCHBEREICH, _SCHRAEGLAGE_SUCHBEREICH + 1e-9, _SCHRAEGLAGE_GROB_SCHRITT,
    )
    grob_varianzen = [_projektionsprofil_varianz(tinte, w) for w in grob_kandidaten]
    bester_grob = float(grob_kandidaten[int(np.argmax(grob_varianzen))])

    fein_kandidaten = np.arange(
        bester_grob - _SCHRAEGLAGE_FEIN_BEREICH,
        bester_grob + _SCHRAEGLAGE_FEIN_BEREICH + 1e-9,
        _SCHRAEGLAGE_FEIN_SCHRITT,
    )
    fein_varianzen = [_projektionsprofil_varianz(tinte, w) for w in fein_kandidaten]
    idx_bester = int(np.argmax(fein_varianzen))
    bester_pil_winkel = float(fein_kandidaten[idx_bester])
    beste_varianz = fein_varianzen[idx_bester]

    mittel = float(np.mean(grob_varianzen + fein_varianzen))
    if mittel <= 0 or beste_varianz / mittel < _SCHRAEGLAGE_MINDEST_VERHAELTNIS:
        return None

    # DE: PIL dreht bei positivem Winkel gegen den Uhrzeigersinn, daher hier
    #     das Vorzeichen umdrehen, um unsere Konvention einzuhalten (siehe
    #     bild_transformieren() oben).
    # EN: PIL rotates counter-clockwise for a positive angle, so the sign
    #     is flipped here to keep our convention (see bild_transformieren()
    #     above).
    return round(-bester_pil_winkel, 1)
