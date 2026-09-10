"""
DE: Erkennung wahrscheinlich leerer Seiten -- haeufig beim automatisierten
    Scannen mit Einzug (Duplex-Scan mit gelegentlich unbedruckter
    Rueckseite, oder ein leeres Trennblatt zwischen Stapeln). Nutzt
    dieselbe "Tinte"-Erkennung wie die Bildbereinigung (core/
    bildbereinigung.py): Pixel dunkler als ein Schwellwert gelten als
    Tinte; liegt ihr Anteil an der Gesamtseite unter einer sehr kleinen
    Grenze, gilt die Seite als wahrscheinlich leer. Bewusst nur eine
    VORSCHLAGS-Funktion (kein automatisches Loeschen ohne Bestaetigung)
    -- Scanner-Rauschen/Staub kann echte Seiten mit sehr wenig Inhalt
    (z. B. eine einzelne Kopfzeile) sonst faelschlich als leer markieren.

EN: Detection of likely-blank pages -- common with automated ADF scanning
    (duplex scans with an occasionally unprinted back side, or a blank
    separator sheet between stacks). Uses the same "ink" detection as
    image cleanup (core/bildbereinigung.py): pixels darker than a
    threshold count as ink; if their share of the whole page falls below
    a very small limit, the page counts as likely blank. Deliberately
    only a SUGGESTION function (no automatic deletion without
    confirmation) -- scanner noise/dust could otherwise falsely flag real
    pages with very little content (e.g. a single header line) as blank.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from .document import WorkingPage
from .rotate import rotiertes_bild

STANDARD_SCHWELLWERT = 128
STANDARD_HOECHSTANTEIL = 0.005  # 0.5 %


def ink_anteil(bild: Image.Image, schwellwert: int) -> float:
    """DE: Anteil (0..1) der Pixel dunkler als `schwellwert`.
    EN: Fraction (0..1) of pixels darker than `schwellwert`."""
    grau = np.asarray(bild.convert("L"), dtype=np.uint8)
    return float(np.count_nonzero(grau < schwellwert)) / grau.size


def ist_wahrscheinlich_leer(
    wp: WorkingPage, schwellwert: int = STANDARD_SCHWELLWERT, hoechstanteil: float = STANDARD_HOECHSTANTEIL,
) -> tuple[bool, float]:
    """
    DE: Rendert die Seite (aktuelle Drehung/Spiegelung) und prueft, ob
        ihr Tinte-Anteil hoechstens `hoechstanteil` betraegt. Liefert
        (wahrscheinlich_leer, tatsaechlicher_anteil).
    EN: Renders the page (current rotation/mirror) and checks whether its
        ink share is at most `hoechstanteil`. Returns
        (likely_blank, actual_share).
    """
    bild, _dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
    anteil = ink_anteil(bild, schwellwert)
    return anteil <= hoechstanteil, anteil
