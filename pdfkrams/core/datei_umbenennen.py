"""
DE: Dateien in einem Ordner einheitlich benennen und durchlaufend
    nummerieren -- Portierung der Kernlogik aus dem urspruenglichen
    benennen.py-Skript (ohne dessen CSV-Protokoll- und Gruppierungs-
    Sonderfaelle, auf das im Alltag Wesentliche reduziert): Dateien
    sammeln, nach Datum oder Name sortieren, durchnummerieren, dabei
    optional an eine bereits im Zielordner vorhandene Nummerierung
    anschliessen, und sicher umbenennen bzw. kopieren.

EN: Rename files in a folder consistently and number them sequentially --
    a port of the core logic from the original benennen.py script (without
    its CSV-log and grouping special cases, reduced to what matters day to
    day): collect files, sort by date or name, number them sequentially,
    optionally continuing an existing numbering already present in the
    target folder, and safely rename resp. copy them.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .datumssortierung import natuerlich, seiten_zeitstempel
from .document import UNTERSTUETZTE_ENDUNGEN, PageSource

# DE: Sortierarten. EN: Sort kinds.
NACH_DATUM = "datum"
NACH_NAME = "name"


@dataclass
class UmbenennungsEintrag:
    alt: Path
    neu: Path


def dateien_sammeln(ordner: Path, rekursiv: bool = False) -> list[Path]:
    """DE: Alle unterstuetzten Dateien in einem Ordner sammeln.
    EN: Collect all supported files in a folder."""
    quelle = ordner.rglob("*") if rekursiv else ordner.glob("*")
    return [f for f in quelle if f.is_file() and f.suffix.lower() in UNTERSTUETZTE_ENDUNGEN]


def _quelle_fuer(pfad: Path) -> PageSource:
    kind = "pdf" if pfad.suffix.lower() == ".pdf" else "image"
    return PageSource(path=pfad, index=0, kind=kind)


def sortieren(dateien: list[Path], art: str) -> list[tuple[Path, str]]:
    """
    DE: Dateien sortieren, liefert Paare (Datei, verwendete Zeitquelle) --
        bei `art=NACH_NAME` ist die Quelle immer "Name".

    EN: Sort files, returns pairs (file, time source used) -- for
        `art=NACH_NAME` the source is always "Name".
    """
    if art == NACH_NAME:
        return [(f, "Name") for f in sorted(dateien, key=lambda f: natuerlich(f.name))]

    bewertet = []
    for f in dateien:
        zeit, quelle = seiten_zeitstempel(_quelle_fuer(f))
        bewertet.append((f, zeit, quelle))
    bewertet.sort(key=lambda t: (t[1], natuerlich(t[0].name)))
    return [(f, quelle) for f, _zeit, quelle in bewertet]


def dateiname(basis: str, nummer: int, stellen: int) -> str:
    """DE: Dateinamen-Kern (ohne Endung) aus Basisname und laufender Nummer bauen.
    EN: Build the filename stem (without extension) from a base name and running number."""
    kern = f"{nummer:0{stellen}d}"
    return f"{basis}_{kern}" if basis else kern


def hoechste_nummer(ordner: Path, basis: str, stellen: int) -> int:
    """DE: Groesste bereits im Ordner vergebene Nummer im erwarteten Namensschema finden.
    EN: Find the highest number already used in the folder matching the expected naming scheme."""
    if not ordner.is_dir():
        return 0
    praefix = f"{basis}_" if basis else ""
    hoechste = 0
    for f in ordner.iterdir():
        if not f.is_file() or not f.stem.startswith(praefix):
            continue
        rest = f.stem[len(praefix):]
        if rest.isdigit():
            hoechste = max(hoechste, int(rest))
    return hoechste


def umbenennungsplan(dateien: list[Path], basis: str, start: int, stellen: int,
                     zielordner: Path | None) -> list[UmbenennungsEintrag]:
    """
    DE: Fuer eine bereits sortierte Dateiliste den Umbenennungsplan
        aufstellen (alte -> neue Pfade), ohne etwas auf der Platte zu
        veraendern. `zielordner=None` bedeutet: an Ort und Stelle umbenennen.

    EN: Build the rename plan (old -> new paths) for an already-sorted
        file list, without touching anything on disk. `zielordner=None`
        means: rename in place.
    """
    plan = []
    nummer = start
    for datei in dateien:
        ziel = zielordner if zielordner is not None else datei.parent
        neu = ziel / (dateiname(basis, nummer, stellen) + datei.suffix.lower())
        plan.append(UmbenennungsEintrag(alt=datei, neu=neu))
        nummer += 1
    return plan


def plan_ausfuehren(plan: list[UmbenennungsEintrag], kopieren: bool) -> None:
    """
    DE: Den Umbenennungsplan tatsaechlich ausfuehren. Beim Verschieben an
        Ort und Stelle laeuft das zweistufig ueber Zwischennamen, damit
        sich Quell- und Zielnamen nicht ins Gehege kommen (z. B. ein
        Tausch von 0001 nach 0002 und umgekehrt).

    EN: Actually carry out the rename plan. When moving in place, this
        happens in two stages via temporary names, so source and target
        names don't collide (e.g. swapping 0001 with 0002 and vice versa).
    """
    for eintrag in plan:
        eintrag.neu.parent.mkdir(parents=True, exist_ok=True)

    if kopieren:
        for eintrag in plan:
            shutil.copy2(eintrag.alt, eintrag.neu)
        return

    zwischenstufe = []
    for i, eintrag in enumerate(plan):
        temp = eintrag.alt.with_name(f".umbenennen_tmp_{i}{eintrag.alt.suffix}")
        eintrag.alt.rename(temp)
        zwischenstufe.append((temp, eintrag.neu))
    for temp, neu in zwischenstufe:
        shutil.move(str(temp), str(neu))


def kollisionen(plan: list[UmbenennungsEintrag]) -> list[Path]:
    """DE: Zielpfade liefern, die bereits existieren und nicht selbst Teil
    des Plans sind -- diese wuerden ueberschrieben und werden deshalb vorher geprueft.
    EN: Return target paths that already exist and aren't themselves part
    of the plan -- these would be overwritten and are therefore checked beforehand."""
    quellen = {e.alt.resolve() for e in plan}
    return [e.neu for e in plan if e.neu.exists() and e.neu.resolve() not in quellen]
