"""
DE: Ergebnis eines Werkzeugs nicht als eine gemeinsame PDF, sondern als
    einzelne, durchnummerierte Dateien speichern -- ein Teil, eine Datei.
    Gedacht fuer Ablaeufe wie den urspruenglichen benennen.py/Hot-Folder-OCR-
    Workflow, wo jede Seite als eigenstaendige Datei weiterverarbeitet wird.
    Wichtig beim Teilen-Werkzeug: eine WorkingPage kann durch Teilung zu
    mehreren Ausgabedateien werden, jede bekommt ihre eigene Nummer.

EN: Save a tool's result not as one combined PDF, but as individual,
    sequentially numbered files -- one part, one file. Meant for workflows
    like the original benennen.py/hot-folder-OCR pipeline, where each page
    is processed further as its own file. Important with the split tool: a
    single WorkingPage can turn into several output files through
    splitting, each gets its own number.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Callable

import pymupdf as fitz  # PyMuPDF (neuer Modulname / new module name)
from PIL import Image

from ..info import pdf_metadaten
from . import arbeitsordner
from .combine import export_pdf
from .document import PageSource, WorkingPage
from .rotate import rotiertes_bild
from .split import teile_bild


def gerenderte_teile(wp: WorkingPage, dpi: float = 300.0) -> list[tuple[Image.Image, float]]:
    """
    DE: Die finalen Bild-Teile einer Arbeitsseite liefern -- nach Drehung,
        Spiegelung und (falls vorhanden) Teilung. Ohne Teilung liefert das
        genau ein Bild, mit Teilung eines pro Rasterzelle.

    EN: Return the final image parts of a working page -- after rotation,
        mirroring, and (if present) splitting. Without splitting this
        returns exactly one image, with splitting one per grid cell.
    """
    bild, tatsaechliche_dpi = rotiertes_bild(wp.source, wp.rotation, wp.spiegel_h, wp.spiegel_v, dpi)
    teile = teile_bild(bild, wp.split) if wp.split is not None else [bild]
    return [(teil, tatsaechliche_dpi) for teil in teile]


def dateiname(basis: str, nummer: int, stellen: int) -> str:
    """DE: Dateinamen (ohne Endung) aus optionalem Basisnamen und laufender Nummer bauen.
    EN: Build a filename (without extension) from an optional base name and running number."""
    kern = f"{nummer:0{stellen}d}"
    return f"{basis}_{kern}" if basis else kern


def _bild_als_pdf(bild: Image.Image, dpi: float, ziel: Path) -> None:
    doc = fitz.open()
    breite_pt = bild.width / dpi * 72.0
    hoehe_pt = bild.height / dpi * 72.0
    seite = doc.new_page(width=breite_pt, height=hoehe_pt)
    puffer = io.BytesIO()
    bild.save(puffer, format="PNG")
    seite.insert_image(seite.rect, stream=puffer.getvalue())
    doc.set_metadata(pdf_metadaten())
    doc.save(ziel)
    doc.close()


def _bild_speichern(bild: Image.Image, dpi: float, ziel: Path) -> None:
    kw = {"dpi": (dpi, dpi)}
    if ziel.suffix.lower() in (".tif", ".tiff"):
        kw["compression"] = "tiff_lzw"
    bild.save(ziel, **kw)


def export_einzeldateien(seiten: list[WorkingPage], zielordner: Path, endung: str,
                         basis: str = "", start: int = 1, stellen: int = 4,
                         fortschritt: Callable[[int, int], None] | None = None) -> list[Path]:
    """
    DE: Jede Arbeitsseite (bzw. bei Teilung jeden ihrer Teile) als eigene,
        durchnummerierte Datei im Zielordner speichern. `endung` bestimmt
        das Format (".pdf", ".jpg", ".tif"/".tiff"). Bei unveraenderten
        PDF-Seiten ohne Teilung und Format ".pdf" bleibt der Vektorinhalt
        erhalten (ueber die bestehende export_pdf-Logik), sonst wird
        gerastert. `fortschritt`, falls angegeben, wird nach jeder
        verarbeiteten Quellseite mit (erledigt, gesamt) aufgerufen. Liefert
        die Liste der geschriebenen Pfade.

    EN: Save each working page (or, when split, each of its parts) as its
        own sequentially numbered file in the target folder. `endung`
        determines the format (".pdf", ".jpg", ".tif"/".tiff"). For
        unmodified PDF pages without splitting and format ".pdf", vector
        content is preserved (via the existing export_pdf logic), otherwise
        the page is rasterized. `fortschritt`, if given, is called with
        (done, total) after each processed source page. Returns the list
        of written paths.
    """
    if not seiten:
        raise ValueError("Keine Seiten zum Exportieren.")

    zielordner.mkdir(parents=True, exist_ok=True)
    endung = endung if endung.startswith(".") else "." + endung
    geschrieben: list[Path] = []
    nummer = start

    for i, wp in enumerate(seiten, start=1):
        if wp.split is None and endung == ".pdf":
            pfad = zielordner / (dateiname(basis, nummer, stellen) + endung)
            export_pdf([wp], pfad)
            geschrieben.append(pfad)
            nummer += 1
        else:
            for bild, dpi in gerenderte_teile(wp):
                pfad = zielordner / (dateiname(basis, nummer, stellen) + endung)
                if endung == ".pdf":
                    _bild_als_pdf(bild, dpi, pfad)
                else:
                    _bild_speichern(bild, dpi, pfad)
                geschrieben.append(pfad)
                nummer += 1

        if fortschritt is not None:
            fortschritt(i, len(seiten))

    return geschrieben


def export_mehrseitige_tiff(seiten: list[WorkingPage], ziel: Path, dpi: float = 300.0,
                            fortschritt: Callable[[int, int], None] | None = None) -> int:
    """
    DE: Alle Seiten (bzw. bei Teilung alle ihre Teile) als EINE mehrseitige
        TIFF-Datei speichern, in der gegebenen Reihenfolge. `fortschritt`,
        falls angegeben, wird waehrend des Renderns nach jeder verarbeiteten
        Quellseite mit (erledigt, gesamt) aufgerufen. Liefert die Anzahl
        geschriebener Seiten.

    EN: Save all pages (or, when split, all of their parts) as ONE
        multi-page TIFF file, in the given order. `fortschritt`, if given,
        is called during rendering with (done, total) after each processed
        source page. Returns the number of pages written.
    """
    if not seiten:
        raise ValueError("Keine Seiten zum Exportieren.")

    bilder: list[Image.Image] = []
    dpis: list[float] = []
    for i, wp in enumerate(seiten, start=1):
        for bild, bild_dpi in gerenderte_teile(wp, dpi):
            bilder.append(bild)
            dpis.append(bild_dpi)
        if fortschritt is not None:
            fortschritt(i, len(seiten))

    erste, rest = bilder[0], bilder[1:]
    erste.save(ziel, save_all=True, append_images=rest, compression="tiff_lzw", dpi=(dpis[0], dpis[0]))
    return len(bilder)


def bild_materialisieren(bild: Image.Image, dpi: float, ordner: Path, name: str) -> PageSource:
    """
    DE: Ein bereits fertig gerendertes Bild als PNG in `ordner` ablegen und
        als PageSource liefern -- der Grundbaustein, um Zwischenergebnisse
        (Teilungen, Heftseiten-Zerlegung) als eigenstaendige, weiter
        bearbeitbare Seiten in die gemeinsame Liste einzusetzen.

    EN: Save an already-rendered image as a PNG in `ordner` and return it
        as a PageSource -- the basic building block for turning
        intermediate results (splits, booklet decomposition) into
        independent, further-editable pages in the shared list.
    """
    ordner.mkdir(parents=True, exist_ok=True)
    dateipfad = ordner / f"{name}.png"
    bild.save(dateipfad, dpi=(dpi, dpi))
    return PageSource(path=dateipfad, index=0, kind="image")


def materialisiere_teilung(wp: WorkingPage) -> list[PageSource]:
    """
    DE: Die Teile einer geteilten (und ggf. gedrehten/gespiegelten)
        Arbeitsseite als eigene Bilddateien im internen Arbeitsordner
        ablegen und als neue PageSource-Liste liefern. Damit lassen sich
        die entstandenen Teile als eigenstaendige Seiten in die gemeinsame
        Liste einsetzen und dort unabhaengig weiterbearbeiten (z. B. ein
        zweites Mal teilen) -- ohne zwischendurch exportieren und neu
        laden zu muessen. Nur sinnvoll, wenn wp.split gesetzt ist.

    EN: Save the parts of a split (and possibly rotated/mirrored) working
        page as individual image files in the internal working folder and
        return them as a new list of PageSource. This lets the resulting
        parts be inserted into the shared list as independent pages and
        edited further there (e.g. split a second time) -- without having
        to export and reload in between. Only meaningful when wp.split is set.
    """
    ziel = arbeitsordner.pfad() / uuid.uuid4().hex
    stamm = wp.source.path.stem
    return [bild_materialisieren(bild, dpi, ziel, f"{stamm}_teil{i}")
           for i, (bild, dpi) in enumerate(gerenderte_teile(wp), start=1)]
