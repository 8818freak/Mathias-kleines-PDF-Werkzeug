"""
DE: Bildbereinigung fuer gescannte Seiten -- Binarisieren (Schwellwert,
    optional automatisch per Otsu-Verfahren vorgeschlagen) und Despeckle
    (kleine dunkle Flecken/Staub entfernen). Beide Schritte sind
    unabhaengig voneinander zuschaltbar: Despeckle laesst sich auch ohne
    Binarisieren anwenden (entfernt dann nur die erkannten Flecken,
    laesst den Rest der Grau-/Farbwerte unveraendert).

    Despeckle ist als morphologisches OEFFNEN (Erodieren, dann Dilatieren)
    auf der Tinte-Maske umgesetzt -- rein mit numpy, ohne scipy: kleine,
    isolierte Flecken (typischerweise 1-2 Pixel) verschwinden beim
    Erodieren komplett und kommen beim Dilatieren nicht zurueck, waehrend
    echte Textstriche (meist mehrere Pixel breit) den Vorgang uebersteht.
    Das ist bewusst kein echtes Verbundkomponenten-Labeling (das koennte
    Flecken bis zu einer bestimmten FLAECHE statt nur DICKE erkennen),
    aber fuer den ueblichen Fall (Staub, Druckpunkte) ausreichend und
    kommt ohne zusaetzliche, schwere Abhaengigkeit aus.

EN: Image cleanup for scanned pages -- binarizing (threshold, optionally
    auto-suggested via Otsu's method) and despeckling (removing small dark
    specks/dust). Both steps can be toggled independently: despeckle can
    be applied without binarizing too (then only removes the detected
    specks, leaving the rest of the gray/color values unchanged).

    Despeckle is implemented as a morphological OPENING (erode, then
    dilate) on the ink mask -- pure numpy, no scipy: small, isolated
    specks (typically 1-2 pixels) disappear entirely during erosion and
    don't come back during dilation, while real text strokes (usually
    several pixels wide) survive the round trip. This is deliberately not
    true connected-component labeling (which could detect specks up to a
    certain AREA rather than just THICKNESS), but is sufficient for the
    common case (dust, print artifacts) and needs no extra, heavy
    dependency.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from .document import WorkingPage
from .rotate import rotiertes_bild
from .schwaerzung import schwaerzungen_anwenden


def otsu_schwellwert(bild: Image.Image) -> int:
    """
    DE: Schlaegt per Otsu-Verfahren einen Schwellwert (0..255) vor, der
        Vorder- (Text/Linien) und Hintergrund am deutlichsten trennt --
        der Wert, der die Zwischen-Klassen-Varianz des Grauwert-Histogramms
        maximiert. Gaengiges Standardverfahren fuer die Binarisierung von
        gescanntem Text.

    EN: Suggests a threshold (0..255) via Otsu's method that most clearly
        separates foreground (text/lines) from background -- the value
        that maximizes the between-class variance of the grayscale
        histogram. Standard method for binarizing scanned text.
    """
    grau = np.asarray(bild.convert("L"), dtype=np.uint8)
    histogramm, _ = np.histogram(grau, bins=256, range=(0, 256))
    gesamt = grau.size
    summe_gesamt = float(np.dot(np.arange(256), histogramm))

    gewicht_hinten = 0
    summe_hinten = 0.0
    beste_varianz = -1.0
    bester_schwellwert = 128
    for t in range(256):
        gewicht_hinten += int(histogramm[t])
        if gewicht_hinten == 0:
            continue
        gewicht_vorne = gesamt - gewicht_hinten
        if gewicht_vorne == 0:
            break
        summe_hinten += t * histogramm[t]
        mittel_hinten = summe_hinten / gewicht_hinten
        mittel_vorne = (summe_gesamt - summe_hinten) / gewicht_vorne
        varianz_zwischen = gewicht_hinten * gewicht_vorne * (mittel_hinten - mittel_vorne) ** 2
        if varianz_zwischen > beste_varianz:
            beste_varianz = varianz_zwischen
            # DE: t+1, nicht t -- t selbst gehoert noch zur "hinten"-Klasse
            #     (<=t), der Schwellwert soll aber mit "< schwellwert"
            #     dieselbe Klasseneinteilung ergeben.
            # EN: t+1, not t -- t itself still belongs to the "back" class
            #     (<=t), but the threshold is meant to be used with
            #     "< schwellwert" to reproduce the same class split.
            bester_schwellwert = t + 1
    return bester_schwellwert


def _erodieren(maske: np.ndarray) -> np.ndarray:
    """DE: Ein Erosionsschritt (4er-Nachbarschaft) -- ein Pixel bleibt nur
    "Tinte", wenn es UND alle vier direkten Nachbarn es auch sind.
    EN: One erosion step (4-neighborhood) -- a pixel stays "ink" only if
    it AND all four direct neighbors are too."""
    gepolstert = np.pad(maske, 1, mode="constant", constant_values=False)
    return (
        gepolstert[1:-1, 1:-1] & gepolstert[:-2, 1:-1] & gepolstert[2:, 1:-1]
        & gepolstert[1:-1, :-2] & gepolstert[1:-1, 2:]
    )


def _dilatieren(maske: np.ndarray) -> np.ndarray:
    """DE: Ein Dilatationsschritt (4er-Nachbarschaft) -- ein Pixel wird
    "Tinte", wenn es selbst ODER einer der vier direkten Nachbarn es ist.
    EN: One dilation step (4-neighborhood) -- a pixel becomes "ink" if it
    itself OR one of the four direct neighbors is."""
    gepolstert = np.pad(maske, 1, mode="constant", constant_values=False)
    return (
        gepolstert[1:-1, 1:-1] | gepolstert[:-2, 1:-1] | gepolstert[2:, 1:-1]
        | gepolstert[1:-1, :-2] | gepolstert[1:-1, 2:]
    )


def _oeffnen(maske: np.ndarray, staerke: int) -> np.ndarray:
    """DE: Morphologisches Oeffnen (staerke-mal erodieren, dann ebenso oft
    dilatieren) -- entfernt Flecken, die duenner als ca. 2*staerke Pixel sind.
    EN: Morphological opening (erode `staerke` times, then dilate the same
    number of times) -- removes specks thinner than roughly 2*staerke pixels."""
    ergebnis = maske
    for _ in range(staerke):
        ergebnis = _erodieren(ergebnis)
    for _ in range(staerke):
        ergebnis = _dilatieren(ergebnis)
    return ergebnis


def seite_bereinigen(
    wp: WorkingPage, schwellwert: int, binarisieren: bool, despeckle_staerke: int,
) -> tuple[Image.Image, float]:
    """
    DE: Seite rendern und bereinigen: alle Pixel dunkler als `schwellwert`
        gelten als "Tinte". Bei `despeckle_staerke > 0` werden davon
        zusammenhaengend duenne Flecken (Staub, Druckpunkte) per
        morphologischem Oeffnen entfernt. Bei `binarisieren=True` wird das
        Ergebnis in reines Schwarzweiss umgewandelt; sonst bleiben Grau-/
        Farbwerte erhalten, nur die per Despeckle entfernten Flecken werden
        aufgehellt. Liefert (Bild, dpi).

    EN: Render and clean up the page: every pixel darker than `schwellwert`
        counts as "ink". If `despeckle_staerke > 0`, thin connected specks
        (dust, print artifacts) are removed via morphological opening. If
        `binarisieren=True`, the result is converted to pure black and
        white; otherwise gray/color values are preserved, only the specks
        removed by despeckle are lightened. Returns (image, dpi).
    """
    # DE: Schwaerzung VOR der Bereinigung anwenden -- ein bereits
    #     eingebranntes, deckend schwarzes Rechteck uebersteht
    #     Binarisieren/Despeckle unveraendert (bleibt durchgehend
    #     "Tinte"), sodass nichts vom urspruenglichen Inhalt durchscheint.
    # EN: Apply redaction before cleanup -- an already-burned-in, fully
    #     opaque black rectangle survives binarizing/despeckling
    #     unchanged (stays "ink" throughout), so nothing of the original
    #     content shows through.
    bild, dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
    bild = schwaerzungen_anwenden(bild, wp.schwaerzungen)
    grau = np.asarray(bild.convert("L"), dtype=np.uint8)
    tinte_vorher = grau < schwellwert

    tinte = _oeffnen(tinte_vorher, despeckle_staerke) if despeckle_staerke > 0 else tinte_vorher

    if binarisieren:
        ergebnis = np.where(tinte, 0, 255).astype(np.uint8)
        ergebnis_bild = Image.fromarray(ergebnis, mode="L").convert("RGB")
    else:
        entfernte_flecken = tinte_vorher & ~tinte
        original = np.asarray(bild, dtype=np.uint8).copy()
        original[entfernte_flecken] = 255
        ergebnis_bild = Image.fromarray(original, mode="RGB")

    return ergebnis_bild, dpi
