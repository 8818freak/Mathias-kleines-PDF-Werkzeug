"""
DE: Ein vergessenes PDF-Oeffnen-Passwort wiederherstellen -- fuer Dateien,
    die man selbst einmal geschuetzt hat, das Passwort dazu aber
    verloren ging. Zwei Strategien:

    1. Woerterbuch-Angriff: eine Liste moeglicher Passwoerter durchgehen
       (z. B. das eigene Passwort-Log, siehe passwort_log.py, oder eine
       Wortliste aus einer Datei) -- schnell, aber nur ein Treffer, wenn
       das Passwort tatsaechlich in der Liste steht.
    2. Brute-Force nach Zeichenvorrat + Laenge: ALLE Kombinationen aus
       gewaehlten Zeichenarten (Ziffern/Klein-/Grossbuchstaben/
       Sonderzeichen) in einem Laengenbereich durchprobieren. Waechst
       exponentiell mit der Laenge -- kombinationsanzahl() liefert die
       Gesamtzahl vorab, damit die GUI eine realistische Zeitschaetzung
       zeigen kann, BEVOR ein aussichtsloser Lauf gestartet wird.

    Jeder einzelne Versuch oeffnet die Datei tatsaechlich mit pikepdf --
    das ist der einzige zuverlaessige Weg, ein Passwort zu pruefen (die
    Geschwindigkeit haengt vom Verschluesselungsverfahren ab: AES-256 ist
    durch die vorgeschriebene Schluesselableitung absichtlich langsamer
    zu pruefen als altes RC4-40, siehe geschwindigkeit_messen()).

EN: Recover a forgotten PDF open password -- for files the user
    protected themselves at some point but lost the password to. Two
    strategies:

    1. Dictionary attack: work through a list of candidate passwords
       (e.g. the user's own password log, see passwort_log.py, or a
       wordlist file) -- fast, but only succeeds if the password is
       actually in the list.
    2. Brute force by character set + length: try ALL combinations of
       chosen character types (digits/lower/upper/special) within a
       length range. Grows exponentially with length --
       kombinationsanzahl() returns the total count up front, so the GUI
       can show a realistic time estimate BEFORE starting a hopeless run.

    Every single attempt actually opens the file with pikepdf -- that's
    the only reliable way to check a password (speed depends on the
    encryption method: AES-256's mandated key derivation is deliberately
    slower to check than old RC4-40, see geschwindigkeit_messen()).
"""

from __future__ import annotations

import itertools
import time
from pathlib import Path
from typing import Callable, Iterable

import pikepdf

# DE: Zeichensatz-Baustein-Name -> tatsaechliche Zeichen. Reihenfolge =
#     Reihenfolge in der GUI.
# EN: Character-set building-block name -> actual characters. Order =
#     order in the GUI.
ZEICHENSAETZE: dict[str, str] = {
    "ziffern": "0123456789",
    "kleinbuchstaben": "abcdefghijklmnopqrstuvwxyz",
    "grossbuchstaben": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "sonderzeichen": "!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~",
}


def kombinationsanzahl(zeichenvorrat: str, min_laenge: int, max_laenge: int) -> int:
    """DE: Gesamtzahl aller Kombinationen im Laengenbereich -- fuer die
        Zeitschaetzung, bevor ein Brute-Force-Lauf gestartet wird.
    EN: Total number of combinations in the length range -- for the time
        estimate before starting a brute-force run."""
    basis = len(zeichenvorrat)
    return sum(basis**laenge for laenge in range(min_laenge, max_laenge + 1))


def _passwort_pruefen(pfad: Path, kandidat: str) -> bool:
    try:
        with pikepdf.open(pfad, password=kandidat):
            return True
    except pikepdf.PasswordError:
        return False


def geschwindigkeit_messen(pfad: Path, anzahl: int = 15) -> float:
    """DE: Misst Versuche/Sekunde an der ECHTEN Zieldatei (mit garantiert
        falschen Kandidaten) -- haengt vom Verschluesselungsverfahren der
        Datei ab, deshalb keine feste Konstante.
    EN: Measures attempts/second against the REAL target file (using
        guaranteed-wrong candidates) -- depends on the file's encryption
        method, hence no fixed constant."""
    start = time.monotonic()
    for i in range(anzahl):
        _passwort_pruefen(pfad, f"__pdfkrams_geschwindigkeitstest_{i}__")
    dauer = time.monotonic() - start
    return anzahl / dauer if dauer > 0 else float("inf")


def woerterbuch_angriff(
    pfad: Path, kandidaten: Iterable[str],
    fortschritt: Callable[[int, int], None] | None = None,
    abbrechen: Callable[[], bool] | None = None,
) -> str | None:
    """DE: Probiert jeden Kandidaten (Duplikate werden ignoriert) als
        Passwort -- liefert den ersten Treffer oder None, wenn keiner
        passt bzw. abgebrochen wurde.
    EN: Tries each candidate (duplicates ignored) as the password --
        returns the first hit, or None if none match or it was
        cancelled."""
    eindeutig = list(dict.fromkeys(kandidaten))
    for i, kandidat in enumerate(eindeutig, start=1):
        if abbrechen is not None and abbrechen():
            return None
        if kandidat and _passwort_pruefen(pfad, kandidat):
            return kandidat
        if fortschritt is not None:
            fortschritt(i, len(eindeutig))
    return None


def brute_force(
    pfad: Path, zeichenvorrat: str, min_laenge: int, max_laenge: int,
    fortschritt: Callable[[int, int], None] | None = None,
    abbrechen: Callable[[], bool] | None = None,
) -> str | None:
    """DE: Probiert ALLE Kombinationen aus `zeichenvorrat` im Laengen-
        bereich [min_laenge, max_laenge], kuerzere zuerst -- liefert den
        ersten Treffer oder None, wenn der ganze Raum erschoepft bzw.
        abgebrochen wurde.
    EN: Tries ALL combinations from `zeichenvorrat` in the length range
        [min_laenge, max_laenge], shorter first -- returns the first
        hit, or None if the whole space was exhausted or it was
        cancelled."""
    gesamt = kombinationsanzahl(zeichenvorrat, min_laenge, max_laenge)
    erledigt = 0
    for laenge in range(min_laenge, max_laenge + 1):
        for kombi in itertools.product(zeichenvorrat, repeat=laenge):
            if abbrechen is not None and abbrechen():
                return None
            kandidat = "".join(kombi)
            if _passwort_pruefen(pfad, kandidat):
                return kandidat
            erledigt += 1
            if fortschritt is not None and (erledigt % 25 == 0 or erledigt == gesamt):
                fortschritt(erledigt, gesamt)
    return None
