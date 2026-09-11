"""
DE: Einfaches, unverschluesseltes Log ueber vergebene PDF-Passwoerter --
    bewusst als Klartext-Liste (siehe Docstring von passwortschutz.py:
    das Log ist fuer die eigene Ablage auf dem eigenen Rechner gedacht,
    keine Tresor-Funktion). Liegt als JSON in den QSettings (siehe
    einstellungen.py) und laesst sich als CSV-Datei exportieren/
    importieren. Dasselbe CSV-Format (nur Dateipfad + Passwort in den
    ersten beiden Spalten) dient auch als Eingabe fuer "Nach Liste
    verschluesseln" -- eine Log-Exportdatei ist also direkt wieder als
    Eingabeliste verwendbar.

EN: Simple, unencrypted log of PDF passwords that have been set --
    deliberately a plaintext list (see passwortschutz.py's docstring:
    the log is meant for the user's own storage on their own machine,
    not a vault). Stored as JSON in QSettings (see einstellungen.py) and
    can be exported/imported as a CSV file. The same CSV format (just
    file path + password in the first two columns) also serves as the
    input for "Encrypt from list" -- so a log export file can directly
    be reused as an input list.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

_CSV_SPALTEN = ("dateipfad", "nutzerpasswort", "eigentuemerpasswort", "verfahren", "zeitpunkt")


@dataclass(frozen=True)
class LogEintrag:
    dateipfad: str
    nutzerpasswort: str
    eigentuemerpasswort: str
    verfahren: str
    zeitpunkt: str

    @staticmethod
    def jetzt(dateipfad: Path, nutzerpasswort: str, eigentuemerpasswort: str, verfahren: str) -> "LogEintrag":
        return LogEintrag(
            dateipfad=str(dateipfad), nutzerpasswort=nutzerpasswort,
            eigentuemerpasswort=eigentuemerpasswort, verfahren=verfahren,
            zeitpunkt=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )


def log_zu_dicts(eintraege: list[LogEintrag]) -> list[dict]:
    """DE: Fuer QSettings (siehe einstellungen.passwort_log_setzen).
    EN: For QSettings (see einstellungen.passwort_log_setzen)."""
    return [asdict(e) for e in eintraege]


def dicts_zu_log(dicts: list[dict]) -> list[LogEintrag]:
    return [LogEintrag(**d) for d in dicts]


def log_als_csv(eintraege: list[LogEintrag]) -> str:
    """DE: Log als CSV-Text (Semikolon-getrennt, Excel-freundlich).
    EN: Log as CSV text (semicolon-separated, Excel-friendly)."""
    puffer = io.StringIO()
    schreiber = csv.writer(puffer, delimiter=";")
    schreiber.writerow(_CSV_SPALTEN)
    for e in eintraege:
        schreiber.writerow([e.dateipfad, e.nutzerpasswort, e.eigentuemerpasswort, e.verfahren, e.zeitpunkt])
    return puffer.getvalue()


def csv_als_log(text: str) -> list[LogEintrag]:
    """DE: CSV-Text (mit oder ohne Kopfzeile) zurueck in Log-Eintraege --
        fehlende Spalten (z. B. eine reine Dateipfad;Passwort-Liste ohne
        Verfahren/Zeitpunkt) werden mit leeren Werten aufgefuellt.
    EN: CSV text (with or without a header row) back into log entries --
        missing columns (e.g. a plain path;password list without
        method/timestamp) are filled in with empty values."""
    zeilen = list(csv.reader(io.StringIO(text), delimiter=";"))
    if zeilen and zeilen[0] and zeilen[0][0].strip().lower() in ("dateipfad", "pfad"):
        zeilen = zeilen[1:]
    ergebnis = []
    for zeile in zeilen:
        if not zeile or not zeile[0].strip():
            continue
        werte = (zeile + [""] * 5)[:5]
        ergebnis.append(LogEintrag(*werte))
    return ergebnis


def liste_aus_csv(text: str) -> list[tuple[Path, str]]:
    """DE: Nur Dateipfad + Passwort aus einem CSV-Text -- Eingabeformat
        fuer "Nach Liste verschluesseln".
    EN: Just file path + password from a CSV text -- input format for
        "Encrypt from list"."""
    return [(Path(e.dateipfad), e.nutzerpasswort) for e in csv_als_log(text) if e.dateipfad]
