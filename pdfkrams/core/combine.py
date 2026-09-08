"""
DE: Baut aus einer Liste von WorkingPage-Objekten (PDF-Seiten und/oder
    Bildern, beliebig gemischt, jede mit eigener Drehung/Spiegelung/
    Teilung) eine einzelne PDF-Datei zusammen. Jede Seite bekommt ihre
    physisch korrekte Groesse (siehe document.seitengroesse_pt).

    Fuer PDF-Seiten ohne Spiegelung, die um 0/90/180/270 Grad gedreht sind,
    wird die Drehung verlustfrei ueber den PDF-eigenen /Rotate-Eintrag
    gesetzt -- der Vektorinhalt bleibt Vektor, es wird nichts gerastert.
    In allen anderen Faellen (freier Winkel, Spiegelung oder Teilung) wird
    die Seite gerastert, transformiert und als Bild eingesetzt.

EN: Assembles a single PDF file from a list of WorkingPage objects (PDF
    pages and/or images, freely mixed, each with its own rotation/mirror/
    split). Each page gets its physically correct size (see
    document.seitengroesse_pt).

    For PDF pages without mirroring that are rotated by 0/90/180/270
    degrees, the rotation is applied losslessly via the PDF's own /Rotate
    entry -- vector content stays vector, nothing gets rasterized. In all
    other cases (free angle, mirroring, or splitting) the page is
    rasterized, transformed, and inserted as an image.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import pymupdf as fitz  # PyMuPDF (neuer Modulname / new module name)
from PIL import Image

from ..info import pdf_metadaten
from .document import WorkingPage, seitengroesse_pt
from .rotate import ist_rechter_winkel, normalisiert, rotiertes_bild
from .split import teile_bild


def _bild_einfuegen(ausgabe: fitz.Document, bild: Image.Image, dpi: float) -> None:
    """DE: Ein PIL-Bild als neue, passend grosse Seite anhaengen.
    EN: Append a PIL image as a new, appropriately sized page."""
    breite_pt = bild.width / dpi * 72.0
    hoehe_pt = bild.height / dpi * 72.0
    seite = ausgabe.new_page(width=breite_pt, height=hoehe_pt)
    puffer = io.BytesIO()
    bild.save(puffer, format="PNG")
    seite.insert_image(seite.rect, stream=puffer.getvalue())


def export_pdf(seiten: list[WorkingPage], ziel: Path,
               fortschritt: Callable[[int, int], None] | None = None) -> None:
    """
    DE: Seiten in der gegebenen Reihenfolge (mit ihren jeweiligen
        Drehungen/Spiegelungen/Teilungen) zu einer PDF-Datei zusammenfuegen
        und unter `ziel` speichern. Eine geteilte Seite wird zu mehreren
        Ausgabeseiten. `fortschritt`, falls angegeben, wird nach jeder
        verarbeiteten Quellseite mit (erledigt, gesamt) aufgerufen -- fuer
        eine Fortschrittsanzeige in der GUI.

    EN: Combine pages in the given order (with their respective
        rotations/mirrors/splits) into a single PDF file and save it to
        `ziel`. A split page becomes multiple output pages. `fortschritt`,
        if given, is called with (done, total) after each processed source
        page -- for a progress display in the GUI.
    """
    if not seiten:
        raise ValueError("Keine Seiten zum Exportieren.")

    ausgabe = fitz.open()
    # DE: Bereits geoeffnete PDF-Quellen zwischenspeichern, damit eine Datei
    #     mit vielen Seiten nicht mehrfach geoeffnet werden muss.
    # EN: Cache already-opened PDF sources so a file with many pages isn't
    #     reopened redundantly.
    offene_pdfs: dict[Path, fitz.Document] = {}
    try:
        for nummer, wp in enumerate(seiten, start=1):
            source = wp.source
            grad = normalisiert(wp.rotation)

            if wp.split is not None:
                # DE: Teilung wirkt auf das bereits gedrehte/gespiegelte
                #     Bild -- dafuer wird immer gerastert.
                # EN: Splitting acts on the already rotated/mirrored image
                #     -- this always requires rasterizing.
                bild, dpi = rotiertes_bild(source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
                for teilbild in teile_bild(bild, wp.split):
                    _bild_einfuegen(ausgabe, teilbild, dpi)

            elif source.kind == "pdf" and not wp.spiegel_h and not wp.spiegel_v and ist_rechter_winkel(grad):
                quelle = offene_pdfs.setdefault(source.path, fitz.open(source.path))
                neue_seite_nr = ausgabe.page_count
                ausgabe.insert_pdf(quelle, from_page=source.index, to_page=source.index)
                if abs(grad) > 1e-6:
                    ausgabe[neue_seite_nr].set_rotation(round(grad) % 360)

            elif wp.unveraendert and source.kind == "image":
                # DE: Unveraendertes Bild -- einfache Platzierung ohne Umweg
                #     ueber Rasterung/Neucodierung.
                # EN: Unmodified image -- simple placement without a detour
                #     through rasterizing/re-encoding.
                breite_pt, hoehe_pt = seitengroesse_pt(source)
                seite = ausgabe.new_page(width=breite_pt, height=hoehe_pt)
                with Image.open(source.path) as im:
                    im.seek(source.index)
                    rgb = im.convert("RGB")
                    puffer = io.BytesIO()
                    rgb.save(puffer, format="PNG")
                    seite.insert_image(seite.rect, stream=puffer.getvalue())

            else:
                # DE: Allgemeiner Fall -- freier Winkel und/oder Spiegelung
                #     und/oder ein Bild, das veraendert wurde: rastern.
                # EN: General case -- free angle and/or mirroring and/or a
                #     modified image: rasterize.
                bild, dpi = rotiertes_bild(source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
                _bild_einfuegen(ausgabe, bild, dpi)

            if fortschritt is not None:
                fortschritt(nummer, len(seiten))

        ausgabe.set_metadata(pdf_metadaten())
        ausgabe.save(ziel)
    finally:
        ausgabe.close()
        for doc in offene_pdfs.values():
            doc.close()
