"""
DE: Sattelheft-Schema fuer Doppelseiten-Scans: aus einer physisch
    gestapelten Reihe von Scans (je ein Scan = eine aufgeklappte Seite mit
    zwei Buchseiten nebeneinander) die korrekte Lesereihenfolge berechnen.
    Portierung des Zahlenschemas aus dem urspruenglichen cut_and_sort_scan.py
    -- dort wurde ueber ImageMagick gerastert und zugeschnitten, hier
    uebernimmt das die vorhandene Dreh-/Teilen-Logik, nur die Formel fuer
    die Lesereihenfolge wird uebernommen.

EN: Saddle-stitch scheme for double-page scans: compute the correct
    reading order from a physically stacked series of scans (each scan =
    one opened spread with two book pages side by side). Port of the
    numbering scheme from the original cut_and_sort_scan.py -- there,
    ImageMagick did the rasterizing and cropping; here the existing
    rotate/split logic handles that, only the reading-order formula is
    carried over.
"""

from __future__ import annotations


def lesereihenfolge(anzahl_bloecke: int) -> list[tuple[int, str]]:
    """
    DE: Liefert die Lesereihenfolge als Liste von (Block-Index, Haelfte).
        Haelfte ist "west" (linke Haelfte des Scans) oder "ost" (rechte
        Haelfte). Block-Index ist 0-basiert, in der Reihenfolge, in der die
        Scans physisch gestapelt bzw. in der Liste angeordnet waren.

    EN: Return the reading order as a list of (block index, half). Half is
        "west" (left half of the scan) or "ost" (right half). Block index
        is 0-based, in the order the scans were physically stacked resp.
        arranged in the list.
    """
    if anzahl_bloecke < 1:
        return []
    gesamt = 2 * anzahl_bloecke
    zuordnung: list[tuple[int, str] | None] = [None] * gesamt
    for idx in range(anzahl_bloecke):
        if idx % 2 == 0:  # DE: erster, dritter, ... Block / EN: first, third, ... block
            west_seite, ost_seite = gesamt - idx, idx + 1
        else:  # DE: zweiter, vierter, ... Block / EN: second, fourth, ... block
            west_seite, ost_seite = idx + 1, gesamt - idx
        zuordnung[west_seite - 1] = (idx, "west")
        zuordnung[ost_seite - 1] = (idx, "ost")
    return zuordnung  # type: ignore[return-value]
