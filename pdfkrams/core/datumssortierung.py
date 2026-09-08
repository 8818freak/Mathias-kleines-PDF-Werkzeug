"""
DE: Fuer eine Seite den verlaesslichsten verfuegbaren Zeitstempel ihrer
    Quelldatei ermitteln, um eine Seitenfolge automatisch nach Aufnahme-
    bzw. Erstellungsdatum sortieren zu koennen -- Portierung der
    Zeitstempel-Logik aus dem urspruenglichen benennen.py-Skript.

    Reihenfolge der Quellen (wie im Original): zuerst der Aufnahme-
    Zeitstempel IM Bild selbst (TIFF-Feld 306 bzw. EXIF, ueberlebt Kopieren
    zwischen Laufwerken), dann das PDF-Erstellungsdatum, zuletzt die
    Dateisystem-Erstellungszeit als Rueckfallebene.

EN: For a page, determine the most reliable available timestamp of its
    source file, to be able to automatically sort a page sequence by
    capture resp. creation date -- a port of the timestamp logic from the
    original benennen.py script.

    Order of sources (as in the original): first the capture timestamp
    INSIDE the image itself (TIFF field 306 resp. EXIF, survives copying
    between drives), then the PDF creation date, finally the filesystem
    creation time as a fallback.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import pymupdf as fitz  # PyMuPDF (neuer Modulname / new module name)
from PIL import Image
from PIL.ExifTags import TAGS

from .document import PageSource


def natuerlich(text: str) -> list:
    """DE: Sortierschluessel, der Zahlen im Namen als Zahlen behandelt.
    So kommt Seite_2 vor Seite_10.
    EN: Sort key that treats numbers in the name as numbers. So Seite_2
    comes before Seite_10."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


def zeit_erstellt(pfad: Path) -> float:
    """DE: Erstellungszeit, so gut das Betriebssystem sie hergibt.
    EN: Creation time, as good as the operating system provides it."""
    st = pfad.stat()
    geburt = getattr(st, "st_birthtime", None)  # macOS, neuere BSD
    if geburt:
        return geburt
    if os.name == "nt":  # Windows: ctime ist die Erstellung
        return st.st_ctime
    return st.st_mtime  # Linux kennt meist keine Erstellungszeit


def zeit_aufnahme(pfad: Path) -> float | None:
    """DE: Aufnahmezeit aus dem Bild selbst (TIFF-Feld 306 bzw. EXIF).
    EN: Capture time from the image itself (TIFF field 306 resp. EXIF)."""
    if pfad.suffix.lower() not in (".tif", ".tiff", ".jpg", ".jpeg"):
        return None
    try:
        with Image.open(pfad) as im:
            roh = None
            tiff = getattr(im, "tag_v2", None)
            if tiff:
                roh = tiff.get(306)  # DateTime
            if not roh:
                exif = im.getexif()
                for schluessel, wert in exif.items():
                    if TAGS.get(schluessel) in ("DateTimeOriginal", "DateTime"):
                        roh = wert
                        break
            if not roh:
                return None
            return datetime.strptime(str(roh).strip(), "%Y:%m:%d %H:%M:%S").timestamp()
    except Exception:
        return None


def zeit_pdf(pfad: Path) -> float | None:
    """DE: Erstellungsdatum aus dem PDF selbst (/CreationDate bzw. /ModDate).
    EN: Creation date from the PDF itself (/CreationDate resp. /ModDate)."""
    if pfad.suffix.lower() != ".pdf":
        return None
    try:
        with fitz.open(pfad) as doc:
            roh = doc.metadata.get("creationDate") or doc.metadata.get("modDate")
        if not roh:
            return None
        text = roh.strip()
        if text.startswith("D:"):
            text = text[2:]
        text = re.sub(r"[Zz+\-].*$", "", text)[:14]
        if len(text) < 8:
            return None
        text = text.ljust(14, "0")
        return datetime.strptime(text, "%Y%m%d%H%M%S").timestamp()
    except Exception:
        return None


def seiten_zeitstempel(source: PageSource) -> tuple[float, str]:
    """
    DE: Verlaesslichsten Zeitstempel einer Seite liefern, als
        (Zeitstempel, Klartext-Quelle) -- Aufnahmezeit bevorzugt, dann
        PDF-Datum, zuletzt Dateisystem-Erstellungszeit als Rueckfall.

    EN: Return a page's most reliable timestamp, as (timestamp,
        human-readable source) -- capture time preferred, then PDF date,
        finally filesystem creation time as a fallback.
    """
    aufnahme = zeit_aufnahme(source.path)
    if aufnahme is not None:
        return aufnahme, "Aufnahme"
    pdf_datum = zeit_pdf(source.path)
    if pdf_datum is not None:
        return pdf_datum, "PDF-Datum"
    return zeit_erstellt(source.path), "erstellt"
