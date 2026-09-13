"""
DE: Eine kleinere PDF-Datei erzeugen, indem jede Seite verlustbehaftet als
    JPEG statt verlustfrei kodiert wird, wahlweise zusaetzlich auf eine
    Hoechstaufloesung verkleinert. Sinnvoll fuer gescannte Dokumente, bei
    denen die verlustfreie PNG-Kodierung sonst sehr grosse Dateien ergibt.

    Nicht sinnvoll fuer echte Vektor-PDFs (Text/Vektorgrafik wird dabei zu
    Pixeln) -- alle Seiten werden hier bewusst gerastert, anders als bei
    combine.export_pdf, das Vektorinhalt wo moeglich erhaelt.

EN: Produce a smaller PDF file by encoding every page lossy as JPEG
    instead of losslessly, optionally also downsampled to a maximum
    resolution. Useful for scanned documents, where lossless PNG encoding
    otherwise results in very large files.

    Not useful for genuine vector PDFs (text/vector graphics get
    rasterized) -- all pages are deliberately rasterized here, unlike
    combine.export_pdf, which preserves vector content where possible.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import pymupdf as fitz  # PyMuPDF (neuer Modulname / new module name)
from PIL import Image

from ..info import pdf_metadaten
from .document import WorkingPage
from .lesezeichen import toc_erzeugen
from .rotate import ist_rechter_winkel, normalisiert, rotiertes_bild
from .schwaerzung import schwaerzungen_anwenden
from .split import teile_bild

# DE: Filter, die ein Bild bereits in einem Format speichern, bei dem eine
#     JPEG-Neukodierung ueberwiegend keinen Sinn ergibt:
#     - JBIG2/CCITT: reiner Schwarzweiss-/Strichinhalt (Text,
#       Strichzeichnungen), verlustfrei und extrem kompakt. JPEG-
#       Neukodierung ist hier so gut wie immer ein Verlust auf ganzer
#       Linie: groesser UND schlechter (Kantenartefakte auf scharfen
#       Text-/Linienkanten), weil JPEG fuer Halbton-/Fotoinhalt gemacht ist.
#     - JPX (JPEG2000): bereits ein verlustbehafteter Foto-Codec, der bei
#       gleicher Qualitaet in aller Regel kompakter kodiert als JPEG --
#       eine Neukodierung als JPEG macht solche Seiten typischerweise
#       GROESSER statt kleiner (das genaue Symptom, das zu diesem Fix
#       gefuehrt hat: eine 912-seitige, ueberwiegend JPX-basierte Vorlage
#       wuchs beim "Verkleinern" von 139 MB auf 349 MB).
# EN: Filters that already store an image in a format where re-encoding as
#     JPEG mostly doesn't make sense:
#     - JBIG2/CCITT: pure black-and-white/line content (text, line art),
#       lossless and extremely compact. Re-encoding as JPEG here is
#       almost always a lose-lose: bigger AND worse (edge artifacts on
#       sharp text/line edges), since JPEG is built for continuous-tone/
#       photo content.
#     - JPX (JPEG2000): already a lossy photo codec that, at matched
#       quality, typically encodes more compactly than JPEG -- re-encoding
#       such pages as JPEG typically makes them BIGGER, not smaller (the
#       exact symptom that led to this fix: a 912-page source dominated
#       by JPX grew from 139 MB to 349 MB when "shrunk").
_BEREITS_EFFIZIENT_FILTER = {"JBIG2Decode", "CCITTFaxDecode", "JPXDecode"}


def _verkleinert(bild: Image.Image, dpi: float, max_dpi: float | None) -> tuple[Image.Image, float]:
    """DE: Bild auf max_dpi herunterskalieren, falls es darueber liegt.
    EN: Downscale an image to max_dpi if it exceeds it."""
    if not max_dpi or dpi <= max_dpi:
        return bild, dpi
    faktor = max_dpi / dpi
    neue_groesse = (max(1, round(bild.width * faktor)), max(1, round(bild.height * faktor)))
    return bild.resize(neue_groesse, Image.LANCZOS), max_dpi


def _bereits_effizient_komprimiert(page: fitz.Page) -> bool:
    """
    DE: Prueft, ob die Seite von einem einzigen, seitenfuellenden Bild
        dominiert wird, das bereits in einem Format vorliegt, bei dem eine
        JPEG-Neukodierung ueberwiegend keinen Sinn ergibt (JBIG2/CCITT fuer
        Schwarzweiss-/Strichinhalt, JPX/JPEG2000 fuer bereits effizient
        komprimierte Fotoseiten) -- solche Seiten sollen unveraendert
        durchgereicht werden statt sie zu JPEG umzukodieren.

    EN: Checks whether the page is dominated by a single page-filling
        image already stored in a format where re-encoding as JPEG mostly
        doesn't make sense (JBIG2/CCITT for black-and-white/line content,
        JPX/JPEG2000 for already efficiently compressed photo pages) --
        such pages should be passed through unchanged instead of being
        re-encoded as JPEG.
    """
    seitenflaeche = page.rect.width * page.rect.height
    if seitenflaeche <= 0:
        return False
    filter_je_xref = {b[0]: b[8] for b in page.get_images(full=True)}
    for eintrag in page.get_image_info(xrefs=True):
        bbox = eintrag["bbox"]
        breite_pt, hoehe_pt = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if breite_pt <= 0 or hoehe_pt <= 0:
            continue
        if (breite_pt * hoehe_pt) / seitenflaeche < 0.9:
            continue
        if filter_je_xref.get(eintrag["xref"]) in _BEREITS_EFFIZIENT_FILTER:
            return True
    return False


def ausgangsgroesse_falls_eindeutig(seiten: list[WorkingPage]) -> int | None:
    """
    DE: Liefert die Dateigroesse der Quelldatei in Bytes, aber NUR, wenn
        `seiten` eindeutig genau einer einzigen Quelldatei entspricht --
        alle ihre Seiten/Frames sind enthalten, keine anderen Dateien sind
        gemischt. Sonst None, weil sich in allen anderen Faellen (Auswahl
        nur eines Teils, mehrere Quelldateien) keine faire Vergleichsgroesse
        angeben liesse. Wird genutzt, um den Nutzer zu warnen, wenn eine
        "verkleinerte" Ausgabe tatsaechlich groesser als das Original ist --
        kann bei bereits effizient komprimierten Quellen (z. B. JPEG2000-
        Scans) durchaus passieren, JPEG ist nicht immer der effizientere
        Codec.

    EN: Return the source file's size in bytes, but ONLY if `seiten`
        unambiguously corresponds to exactly one single source file -- all
        of its pages/frames are included, no other files are mixed in.
        Otherwise None, since in every other case (only part of a file
        selected, several source files) there's no fair size to compare
        against. Used to warn the user when a "shrunk" export actually
        ends up larger than the original -- which can genuinely happen for
        already efficiently compressed sources (e.g. JPEG2000 scans), as
        JPEG isn't always the more efficient codec.
    """
    quelldateien = {wp.source.path for wp in seiten}
    if len(quelldateien) != 1:
        return None
    pfad = next(iter(quelldateien))
    if pfad.suffix.lower() == ".pdf":
        with fitz.open(pfad) as doc:
            gesamt_seiten = doc.page_count
    else:
        with Image.open(pfad) as im:
            gesamt_seiten = getattr(im, "n_frames", 1)
    if {wp.source.index for wp in seiten} != set(range(gesamt_seiten)):
        return None  # DE: nur ein Teil der Datei / EN: only part of the file
    return pfad.stat().st_size


def codec_analyse(seiten: list[WorkingPage]) -> tuple[int, int]:
    """
    DE: Zaehlt, wie viele der gegebenen Seiten bereits in einem Format
        vorliegen, bei dem eine JPEG-Neukodierung ueberwiegend keinen Sinn
        ergibt (siehe _bereits_effizient_komprimiert()) -- fuer einen
        proaktiven Hinweis im Werkzeug, BEVOR eine (bei vielen Seiten
        langwierige) Komprimierung tatsaechlich angestossen wird. Reine
        Metadaten-Abfrage ohne Rasterung, daher auch bei vielen hundert
        Seiten schnell genug fuer einen Aufruf direkt bei Auswahlaenderung.
        Liefert (Anzahl bereits effizient, Gesamtzahl).

    EN: Counts how many of the given pages are already stored in a format
        where JPEG re-encoding mostly doesn't make sense (see
        _bereits_effizient_komprimiert()) -- for a proactive hint in the
        tool, BEFORE a (for many pages, lengthy) compression is actually
        triggered. Pure metadata lookup without rasterizing, so fast
        enough even for several hundred pages to call directly on
        selection change. Returns (count already efficient, total count).
    """
    offene_pdfs: dict[Path, fitz.Document] = {}
    bereits_effizient = 0
    try:
        for wp in seiten:
            source = wp.source
            if source.kind != "pdf":
                continue
            grad = normalisiert(wp.rotation)
            unveraendert = (
                not wp.schwaerzungen and wp.split is None and not wp.spiegel_h and not wp.spiegel_v
                and ist_rechter_winkel(grad)
            )
            if not unveraendert:
                continue
            quelle = offene_pdfs.setdefault(source.path, fitz.open(source.path))
            if _bereits_effizient_komprimiert(quelle[source.index]):
                bereits_effizient += 1
    finally:
        for doc in offene_pdfs.values():
            doc.close()
    return bereits_effizient, len(seiten)


def export_pdf_komprimiert(seiten: list[WorkingPage], ziel: Path, jpeg_qualitaet: int = 75,
                           max_dpi: float | None = 200.0,
                           fortschritt: Callable[[int, int], None] | None = None,
                           dokument_metadaten: dict[str, str] | None = None) -> tuple[int, int]:
    """
    DE: Seiten wie combine.export_pdf zusammensetzen, dabei aber jede
        Seite als JPEG mit `jpeg_qualitaet` (1-95) kodieren und optional
        auf `max_dpi` verkleinern (None = nicht verkleinern). Ausnahme:
        unveraenderte PDF-Seiten, die bereits in einem Format vorliegen, bei
        dem JPEG-Neukodierung ueberwiegend keinen Sinn ergibt (JBIG2/CCITT
        fuer Schwarzweiss-/Strichinhalt, JPX/JPEG2000 fuer bereits
        effizient komprimierte Fotoseiten), werden unveraendert
        durchgereicht -- JPEG waere hier so gut wie immer groesser (und bei
        JBIG2/CCITT zusaetzlich schlechter), siehe
        _bereits_effizient_komprimiert(). `dokument_metadaten`
        (optional, siehe core/metadaten.py's pdf_felder()) ergaenzt Titel/
        Autor/Thema/Stichwoerter; Lesezeichen (siehe WorkingPage.
        lesezeichen_titel) werden wie bei combine.export_pdf uebernommen.
        Liefert (Anzahl_Ausgabeseiten, Dateigroesse_in_Bytes).

    EN: Assemble pages like combine.export_pdf, but encode every page as
        JPEG at `jpeg_qualitaet` (1-95) and optionally downscale to
        `max_dpi` (None = no downscaling). Exception: unmodified PDF pages
        already stored in a format where JPEG re-encoding mostly doesn't
        make sense (JBIG2/CCITT for black-and-white/line content, JPX/
        JPEG2000 for already efficiently compressed photo pages) are
        passed through unchanged -- JPEG would almost always be bigger
        (and, for JBIG2/CCITT, also worse) there, see
        _bereits_effizient_komprimiert(). `dokument_metadaten`
        (optional, see core/metadaten.py's pdf_felder()) adds title/author/
        subject/keywords; bookmarks (see WorkingPage.lesezeichen_titel) are
        carried over the same way as in combine.export_pdf. Returns
        (output_page_count, file_size_in_bytes).
    """
    if not seiten:
        raise ValueError("Keine Seiten zum Exportieren.")

    ausgabe = fitz.open()
    anzahl_seiten = 0
    offene_pdfs: dict[Path, fitz.Document] = {}
    toc_rohdaten: list[tuple[int, str, int]] = []
    try:
        for i, wp in enumerate(seiten, start=1):
            source = wp.source
            grad = normalisiert(wp.rotation)
            erste_ausgabeseite = ausgabe.page_count
            unveraendert_pdf_seite = (
                not wp.schwaerzungen and wp.split is None and not wp.spiegel_h and not wp.spiegel_v
                and source.kind == "pdf" and ist_rechter_winkel(grad)
            )
            if unveraendert_pdf_seite:
                quelle = offene_pdfs.setdefault(source.path, fitz.open(source.path))
                if _bereits_effizient_komprimiert(quelle[source.index]):
                    neue_seite_nr = ausgabe.page_count
                    ausgabe.insert_pdf(quelle, from_page=source.index, to_page=source.index)
                    if abs(grad) > 1e-6:
                        ausgabe[neue_seite_nr].set_rotation(round(grad) % 360)
                    anzahl_seiten += 1
                    if wp.lesezeichen_titel:
                        toc_rohdaten.append((wp.lesezeichen_ebene, wp.lesezeichen_titel, erste_ausgabeseite + 1))
                    if fortschritt is not None:
                        fortschritt(i, len(seiten))
                    continue

            # DE: Schwaerzung VOR dem Zerschneiden auf das Gesamtbild
            #     anwenden -- die Rechtecke sind als Anteile der GANZEN
            #     Seite definiert, nicht je Teilstueck.
            # EN: Apply redaction to the WHOLE image before splitting --
            #     the rectangles are defined as fractions of the ENTIRE
            #     page, not per split part.
            bild, dpi = rotiertes_bild(source, wp.rotation, wp.spiegel_h, wp.spiegel_v)
            bild = schwaerzungen_anwenden(bild, wp.schwaerzungen)
            teile = teile_bild(bild, wp.split) if wp.split is not None else [bild]

            for teil in teile:
                teil, effektive_dpi = _verkleinert(teil, dpi, max_dpi)
                breite_pt = teil.width / effektive_dpi * 72.0
                hoehe_pt = teil.height / effektive_dpi * 72.0
                seite = ausgabe.new_page(width=breite_pt, height=hoehe_pt)
                puffer = io.BytesIO()
                teil.convert("RGB").save(puffer, format="JPEG", quality=jpeg_qualitaet)
                seite.insert_image(seite.rect, stream=puffer.getvalue())
                anzahl_seiten += 1

            if wp.lesezeichen_titel:
                toc_rohdaten.append((wp.lesezeichen_ebene, wp.lesezeichen_titel, erste_ausgabeseite + 1))

            if fortschritt is not None:
                fortschritt(i, len(seiten))

        # DE: garbage=4 entfernt nicht mehr benutzte Objekte, deflate
        #     komprimiert die PDF-eigenen Datenstroeme zusaetzlich.
        # EN: garbage=4 drops unused objects, deflate additionally
        #     compresses the PDF's own data streams.
        if toc_rohdaten:
            ausgabe.set_toc(toc_erzeugen(toc_rohdaten))
        ausgabe.set_metadata(pdf_metadaten(dokument_metadaten))
        ausgabe.save(ziel, garbage=4, deflate=True, use_objstms=1)
    finally:
        ausgabe.close()
        for doc in offene_pdfs.values():
            doc.close()

    return anzahl_seiten, ziel.stat().st_size


def strukturell_komprimieren(quelle: Path, ziel: Path) -> tuple[int, int]:
    """
    DE: Eine bestehende PDF-Datei verlustfrei verkleinern -- entfernt nicht
        mehr benutzte bzw. doppelte Objekte und komprimiert unkomprimierte
        Datenstroeme, ohne Bilder neu zu kodieren oder irgendetwas an der
        Darstellung zu aendern. Eigenstaendige Funktion (kein automatischer
        Teil des normalen Exports), da sie separat angestossen werden soll.
        Liefert (Groesse_vorher, Groesse_nachher) in Bytes.

    EN: Losslessly shrink an existing PDF file -- removes unused resp.
        duplicate objects and compresses uncompressed data streams,
        without re-encoding any images or changing anything about how it
        looks. Standalone function (not an automatic part of normal
        export), since it's meant to be triggered separately. Returns
        (size_before, size_after) in bytes.
    """
    groesse_vorher = quelle.stat().st_size
    with fitz.open(quelle) as pdf:
        pdf.set_metadata(pdf_metadaten())
        # DE: use_objstms=1 haelt die kompakte Objekt-Stream-Struktur bei --
        #     ohne dieses Flag schreibt PyMuPDF bei vielseitigen PDFs die
        #     Objekte in einem weniger kompakten Format neu, was die
        #     Garbage-Collection/Deflate-Ersparnis leicht ueberkompensieren
        #     und die Datei am Ende sogar VERGROESSERN kann.
        # EN: use_objstms=1 preserves the compact object-stream structure --
        #     without this flag, PyMuPDF rewrites objects in a less compact
        #     format for many-page PDFs, which can slightly outweigh the
        #     garbage-collection/deflate savings and end up making the file
        #     LARGER instead of smaller.
        pdf.save(ziel, garbage=4, deflate=True, use_objstms=1)
    return groesse_vorher, ziel.stat().st_size
