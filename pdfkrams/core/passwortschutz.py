"""
DE: Passwortschutz zu PDF-Dateien HINZUFUEGEN -- das Gegenstueck zu
    core/reparatur.py's passwort_entfernen(). Ein Verfahren (RC4/AES,
    Schluessellaenge) plus Oeffnen-Passwort (User) und Rechte-Passwort
    (Owner) sowie einzeln schaltbare Berechtigungen (Drucken/Kopieren/
    Bearbeiten). Owner-Passwort ist die Instanz, die trotz gesetzter
    Einschraenkungen alles darf; bleibt es leer, wird das User-Passwort
    auch als Owner-Passwort verwendet (sonst waere die Datei ohne
    eigenes Rechte-Passwort unterwegs, was die meisten Betrachter als
    inkonsistent behandeln).

    Zusaetzlich zwei Stapel-Varianten: einen ganzen Ordner (samt
    Unterordnern) mit demselben Passwort versehen, oder eine Liste aus
    (Datei, individuelles Passwort)-Paaren abarbeiten. Beide arbeiten
    IN-PLACE (ueberschreiben die Originaldatei) -- das ist bewusst so,
    weil das der einzige Weg ist, "diese Dateien sind ab jetzt
    geschuetzt" zu erreichen, ohne Duplikate anzulegen; die GUI warnt
    davor, bevor ein Stapel gestartet wird.

EN: ADD password protection to PDF files -- the counterpart to
    core/reparatur.py's passwort_entfernen(). A method (RC4/AES, key
    length) plus an open password (user) and a permissions password
    (owner), and individually toggleable permissions (print/copy/edit).
    The owner password is the one that can do everything despite the
    restrictions; if left empty, the user password is also used as the
    owner password (otherwise the file would ship without its own
    permissions password, which most viewers treat as inconsistent).

    Plus two batch variants: protect an entire folder (including
    subfolders) with the same password, or work through a list of
    (file, individual password) pairs. Both operate IN-PLACE (overwrite
    the original file) -- deliberately so, since that's the only way to
    achieve "these files are now protected" without creating duplicates;
    the GUI warns about this before a batch run starts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pikepdf

# DE: Anzeigename -> (Revision, AES statt RC4). R=2/3 sind reines RC4
#     (40- bzw. 128-Bit), R=4 erlaubt AES-128, R=6 ist immer AES-256.
#     Reihenfolge = Reihenfolge im Auswahlfeld der GUI.
# EN: Display name -> (revision, AES instead of RC4). R=2/3 are plain
#     RC4 (40- resp. 128-bit), R=4 allows AES-128, R=6 is always
#     AES-256. Order = order in the GUI's dropdown.
VERFAHREN: dict[str, tuple[int, bool]] = {
    "rc4_40": (2, False),
    "rc4_128": (3, False),
    "aes_128": (4, True),
    "aes_256": (6, True),
}
STANDARD_VERFAHREN = "aes_256"


@dataclass(frozen=True)
class Schutzeinstellungen:
    """DE: Alle Einstellungen fuer eine Verschluesselung ausser dem/den
        eigentlichen Oeffnen-Passwort/-Passwoertern (das kommt je nach
        Aktion aus einem einzelnen Feld, einem Ordner-weiten Feld oder
        einer Liste).
    EN: All settings for an encryption run except the actual open
        password/passwords (that comes from a single field, a folder-wide
        field, or a list, depending on the action)."""

    verfahren: str = STANDARD_VERFAHREN
    owner_passwort: str = ""
    drucken_erlauben: bool = True
    kopieren_erlauben: bool = True
    bearbeiten_erlauben: bool = True


def _verschluesselung(user_passwort: str, e: Schutzeinstellungen) -> pikepdf.Encryption:
    revision, aes = VERFAHREN[e.verfahren]
    erlaubt = pikepdf.Permissions(
        accessibility=True,
        extract=e.kopieren_erlauben,
        modify_annotation=e.bearbeiten_erlauben,
        modify_assembly=e.bearbeiten_erlauben,
        modify_form=e.bearbeiten_erlauben,
        modify_other=e.bearbeiten_erlauben,
        print_lowres=e.drucken_erlauben,
        print_highres=e.drucken_erlauben,
    )
    return pikepdf.Encryption(
        owner=e.owner_passwort or user_passwort,
        user=user_passwort,
        R=revision, allow=erlaubt, aes=aes,
    )


def passwort_hinzufuegen(quelle: Path, ziel: Path, user_passwort: str, e: Schutzeinstellungen) -> None:
    """DE: Oeffnet `quelle` (unverschluesselt oder mit bereits bekanntem
        Passwort) und speichert sie mit neuem Passwortschutz als `ziel`.
    EN: Opens `quelle` (unencrypted, or already known password) and saves
        it with new password protection as `ziel`."""
    with pikepdf.open(quelle, allow_overwriting_input=(quelle == ziel)) as pdf:
        pdf.save(ziel, encryption=_verschluesselung(user_passwort, e))


def ordner_verschluesseln(
    ordner: Path, user_passwort: str, e: Schutzeinstellungen,
    fortschritt: Callable[[int, int], None] | None = None,
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """
    DE: Verschluesselt jede PDF-Datei unter `ordner` (rekursiv, alle
        Unterordner) IN-PLACE mit demselben `user_passwort`. Liefert
        (erfolgreiche Pfade, [(Pfad, Fehlertext), ...]) -- eine einzelne
        fehlschlagende Datei (z. B. bereits verschluesselt, oder gerade
        durch ein anderes Programm geoeffnet) bricht den restlichen
        Stapel nicht ab.
    EN: Encrypts every PDF file under `ordner` (recursively, all
        subfolders) IN-PLACE with the same `user_passwort`. Returns
        (successful paths, [(path, error text), ...]) -- a single
        failing file (e.g. already encrypted, or currently open in
        another program) doesn't abort the rest of the batch.
    """
    dateien = sorted(ordner.rglob("*.pdf"))
    erfolgreich: list[Path] = []
    fehler: list[tuple[Path, str]] = []
    for i, pfad in enumerate(dateien, start=1):
        try:
            passwort_hinzufuegen(pfad, pfad, user_passwort, e)
            erfolgreich.append(pfad)
        except Exception as exc:  # noqa: BLE001 -- eine Datei darf den Stapel nicht stoppen
            fehler.append((pfad, str(exc)))
        if fortschritt is not None:
            fortschritt(i, len(dateien))
    return erfolgreich, fehler


def liste_verschluesseln(
    eintraege: list[tuple[Path, str]], e: Schutzeinstellungen,
    fortschritt: Callable[[int, int], None] | None = None,
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """
    DE: Verschluesselt jede in `eintraege` genannte Datei IN-PLACE mit
        ihrem jeweils EIGENEN Passwort (zweiter Wert des Tupels).
        Rueckgabe wie ordner_verschluesseln().
    EN: Encrypts every file named in `eintraege` IN-PLACE with its own
        individual password (second value of the tuple). Return value
        like ordner_verschluesseln().
    """
    erfolgreich: list[Path] = []
    fehler: list[tuple[Path, str]] = []
    for i, (pfad, user_passwort) in enumerate(eintraege, start=1):
        try:
            passwort_hinzufuegen(pfad, pfad, user_passwort, e)
            erfolgreich.append(pfad)
        except Exception as exc:  # noqa: BLE001 -- eine Datei darf den Stapel nicht stoppen
            fehler.append((pfad, str(exc)))
        if fortschritt is not None:
            fortschritt(i, len(eintraege))
    return erfolgreich, fehler
