"""
DE: Zwei eigenstaendige Werkzeuge fuer beschaedigte bzw. gesperrte
    PDF-Dateien, unabhaengig von der gemeinsamen Seitenliste -- passend
    zu den bereits vorhandenen Einzeldatei-Werkzeugen "PDF/A eigenstaendig"
    und "Struktur-Kompression eigenstaendig" (siehe pdfa.py bzw.
    komprimierung.py).

    Reparatur: pikepdf (bzw. das dahinterliegende qpdf) rekonstruiert beim
    Oeffnen automatisch eine kaputte Querverweistabelle (xref), einen
    falschen/fehlenden startxref-Offset oder eine defekte inkrementelle
    Aktualisierung -- die mit Abstand haeufigsten Ursachen fuer "PDF laesst
    sich nicht oeffnen". Schlaegt das fehl, wird zusaetzlich PyMuPDF
    versucht, das eine eigene, andersartige Wiederherstellungslogik hat.
    Fuer BEIDE Bibliotheken unlesbare Dateien (z. B. mitten im Schreiben
    abgebrochene/abgeschnittene Dateien ohne jede Seitenstruktur) lassen
    sich damit nicht retten -- eine Reparatur ist kein Ersatz fuer ein
    Backup.

    Passwort entfernen: setzt voraus, dass das Passwort BEKANNT ist (kein
    Passwort-Knacken) -- oeffnet damit und speichert ohne Verschluesselung
    neu.

EN: Two standalone tools for damaged resp. locked PDF files, independent
    of the shared page list -- matching the existing single-file tools
    "PDF/A standalone" and "Structural compression standalone" (see
    pdfa.py resp. komprimierung.py).

    Repair: pikepdf (i.e. the underlying qpdf) automatically reconstructs
    a broken cross-reference table (xref), a wrong/missing startxref
    offset, or a broken incremental update when opening -- by far the
    most common causes of "PDF won't open". If that fails, PyMuPDF is
    tried as well, which has its own, different recovery logic. Files
    unreadable by BOTH libraries (e.g. files cut off mid-write with no
    page structure left at all) can't be rescued this way -- a repair
    tool is no substitute for a backup.

    Remove password: requires the password to be KNOWN (no password
    cracking) -- opens with it and saves again without encryption.
"""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pymupdf as fitz

from ..info import pdf_metadaten


class ReparaturFehlgeschlagen(Exception):
    """DE: Weder pikepdf noch PyMuPDF konnten die Datei lesen.
    EN: Neither pikepdf nor PyMuPDF could read the file."""


def ist_verschluesselt(pfad: Path) -> bool:
    """DE: Ob eine PDF-Datei ein Passwort zum Oeffnen benoetigt.
    EN: Whether a PDF file requires a password to open."""
    with fitz.open(pfad) as doc:
        return bool(doc.needs_pass)


def pdf_reparieren(quelle: Path, ziel: Path) -> int:
    """
    DE: Versucht, `quelle` zu reparieren und als neue, saubere Datei unter
        `ziel` zu speichern. Erst pikepdf/qpdf (staerker bei xref-/
        Trailer-Problemen), bei Fehlschlag PyMuPDF (staerker bei manchen
        Strom-/Objektfehlern) als zweiter Versuch. Liefert die Seitenzahl
        der reparierten Datei; loest ReparaturFehlgeschlagen aus, wenn
        beide Bibliotheken scheitern.
    EN: Attempts to repair `quelle` and save it as a new, clean file at
        `ziel`. Tries pikepdf/qpdf first (stronger for xref/trailer
        issues), then PyMuPDF as a second attempt on failure (stronger
        for some stream/object errors). Returns the repaired file's page
        count; raises ReparaturFehlgeschlagen if both libraries fail.
    """
    try:
        with pikepdf.open(quelle) as pdf:
            pdf.save(ziel)
        with fitz.open(ziel) as geprueft:
            return geprueft.page_count
    except Exception as pikepdf_fehler:  # noqa: BLE001 -- bewusst breit, zweiter Versuch folgt
        try:
            with fitz.open(quelle) as pdf:
                pdf.set_metadata(pdf_metadaten())
                pdf.save(ziel, garbage=4, deflate=True)
                return pdf.page_count
        except Exception as fitz_fehler:  # noqa: BLE001 -- beide Versuche gescheitert
            raise ReparaturFehlgeschlagen(
                f"pikepdf: {pikepdf_fehler}\nPyMuPDF: {fitz_fehler}"
            ) from fitz_fehler


def passwort_entfernen(quelle: Path, ziel: Path, passwort: str) -> None:
    """
    DE: Oeffnet `quelle` mit dem bekannten `passwort` und speichert sie
        unverschluesselt als `ziel`. Loest pikepdf.PasswordError aus, wenn
        das Passwort falsch ist.
    EN: Opens `quelle` with the known `passwort` and saves it unencrypted
        as `ziel`. Raises pikepdf.PasswordError if the password is wrong.
    """
    with pikepdf.open(quelle, password=passwort) as pdf:
        pdf.save(ziel, encryption=False)
