"""
DE: Quell-unabhaengiges Seitenmodell. Eine "Seite" ist entweder eine Seite
    innerhalb einer PDF-Datei oder ein Einzelbild (auch ein Frame aus einem
    mehrseitigen TIFF). Bewusst ohne Qt-Abhaengigkeit, damit sich diese Logik
    ohne GUI testen und in anderen Werkzeugen wiederverwenden laesst.

EN: Source-independent page model. A "page" is either a page inside a PDF
    file or a single image (including one frame of a multi-page TIFF).
    Deliberately kept free of Qt dependencies so this logic can be tested
    without a GUI and reused by other tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz  # PyMuPDF (neuer Modulname / new module name)
from PIL import Image

# DE: Unterstuetzte Dateiendungen, getrennt nach Bild und PDF.
# EN: Supported file extensions, split into image and PDF.
BILD_ENDUNGEN = {".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".png"}
PDF_ENDUNG = ".pdf"
UNTERSTUETZTE_ENDUNGEN = BILD_ENDUNGEN | {PDF_ENDUNG}

# DE: Annahme, wenn ein Bild keine Aufloesung (DPI) in den Metadaten traegt.
# EN: Assumption used when an image carries no resolution (DPI) metadata.
STANDARD_DPI = 300.0


@dataclass(frozen=True)
class PageSource:
    """
    DE: Verweis auf eine einzelne Seite in einer Quelldatei -- entweder eine
        PDF-Seite oder ein Bild-Frame. Traegt selbst keine Bilddaten, nur den
        Verweis darauf; das haelt Listen von hunderten Seiten leichtgewichtig.

    EN: Reference to a single page inside a source file -- either a PDF page
        or an image frame. Carries no pixel data itself, only the reference;
        this keeps lists of hundreds of pages lightweight.
    """

    path: Path
    index: int  # DE: 0-basiert / EN: zero-based (PDF page or image frame)
    kind: str  # DE: "pdf" oder "image" / EN: "pdf" or "image"

    @property
    def label(self) -> str:
        """DE: Anzeigename fuer Listen/Vorschau. EN: Display name for lists/preview."""
        return f"{self.path.name} · Seite {self.index + 1}"


@dataclass
class SplitSpec:
    """
    DE: Beschreibt, wie eine Seite in ein Raster aus Teilen zerschnitten
        werden soll -- senkrechte und waagerechte Schnittlinien unabhaengig
        voneinander, beide gleichzeitig moeglich (fuer ein echtes Zeilen x
        Spalten-Raster, z. B. eine Anleitung mit mehreren Seiten pro
        gescanntem Blatt). `positionen_v` sind die senkrechten Schnittlinien
        (trennen Spalten), `positionen_h` die waagerechten (trennen Zeilen),
        jeweils als Anteil (0..1) der Breite bzw. Hoehe, OHNE die Raender 0
        und 1. Eine leere Liste bedeutet "keine Schnitte auf dieser Achse".
        Die Positionen innerhalb einer Achse muessen nicht gleichmaessig
        verteilt sein -- jede Zeile/Spalte kann unterschiedlich breit sein.

    EN: Describes how a page should be cut into a grid of parts --
        vertical and horizontal cut lines independent of each other, both
        possible at once (for a true row x column grid, e.g. a manual with
        several pages per scanned sheet). `positionen_v` are the vertical
        cut lines (separate columns), `positionen_h` the horizontal ones
        (separate rows), each as a fraction (0..1) of width resp. height,
        EXCLUDING the 0 and 1 edges. An empty list means "no cuts on that
        axis". Positions within one axis need not be evenly spaced -- each
        row/column can be a different size.
    """

    positionen_v: list[float] = field(default_factory=list)
    positionen_h: list[float] = field(default_factory=list)


@dataclass
class WorkingPage:
    """
    DE: Eine Seite in der Arbeitsliste eines Werkzeugs, zusammen mit den
        Veraenderungen, die der Nutzer bislang daran vorgenommen hat (Drehung,
        Spiegelung, Teilung, Nummerierung). Bewusst veraenderlich (kein
        frozen dataclass wie PageSource), da genau diese Felder von der GUI
        laufend angepasst werden -- z. B. beim Ziehen im Dreh- oder
        Teilen-Werkzeug.

    EN: A page in a tool's working list, together with the edits the user
        has made to it so far (rotation, mirroring, splitting, numbering).
        Deliberately mutable (unlike the frozen PageSource) since exactly
        these fields are continuously adjusted by the GUI -- e.g. while
        dragging in the rotate or split tool.
    """

    source: PageSource
    rotation: float = 0.0  # DE: Grad im Uhrzeigersinn / EN: degrees clockwise
    spiegel_h: bool = False  # DE: horizontal gespiegelt / EN: flipped horizontally
    spiegel_v: bool = False  # DE: vertikal gespiegelt / EN: flipped vertically
    split: SplitSpec | None = None  # DE: Teilung, falls gewuenscht / EN: split, if requested
    # DE: Zielnummer fuer die Neuanordnung einer durcheinandergeratenen
    #     Seitenfolge (Nummerieren-Werkzeug). Wirkt sich nur auf die
    #     Reihenfolge in der Liste aus, veraendert das Seitenbild nicht.
    # EN: Target number for rearranging a scrambled page sequence
    #     (numbering tool). Only affects the order in the list, never
    #     changes the page image.
    ziel_nummer: int | None = None

    @property
    def unveraendert(self) -> bool:
        """DE: True, wenn weder gedreht, gespiegelt noch geteilt wurde.
        EN: True if neither rotated, mirrored, nor split."""
        return self.rotation == 0.0 and not self.spiegel_h and not self.spiegel_v and self.split is None


def ist_unterstuetzt(path: Path) -> bool:
    """DE: Prueft, ob das Dateiformat verarbeitet werden kann.
    EN: Checks whether the file format can be processed."""
    return path.suffix.lower() in UNTERSTUETZTE_ENDUNGEN


def datei_aufschluesseln(path: Path) -> list[PageSource]:
    """
    DE: Alle Seiten bzw. Frames einer Datei als PageSource-Liste liefern.
        Bei PDF ist das eine Seite pro Dokumentseite, bei Bildern eine
        PageSource pro Frame (bei TIFF koennen das mehrere sein).

    EN: Return all pages/frames of a file as a list of PageSource objects.
        For PDFs that's one entry per document page; for images it's one
        entry per frame (a TIFF may contain several).
    """
    endung = path.suffix.lower()
    if endung == PDF_ENDUNG:
        with fitz.open(path) as doc:
            anzahl = doc.page_count
        return [PageSource(path, i, "pdf") for i in range(anzahl)]
    if endung in BILD_ENDUNGEN:
        with Image.open(path) as im:
            anzahl = getattr(im, "n_frames", 1)
        return [PageSource(path, i, "image") for i in range(anzahl)]
    raise ValueError(f"Nicht unterstuetztes Dateiformat: {path.suffix}")


def bild_dpi(im: Image.Image) -> tuple[float, float]:
    """DE: Aufloesung aus den Bildmetadaten lesen, sonst STANDARD_DPI.
    EN: Read resolution from image metadata, falling back to STANDARD_DPI."""
    dpi = im.info.get("dpi")
    if dpi and dpi[0] and dpi[1]:
        return float(dpi[0]), float(dpi[1])
    return STANDARD_DPI, STANDARD_DPI


def seitengroesse_pt(source: PageSource) -> tuple[float, float]:
    """
    DE: Physische Seitengroesse in PDF-Punkten (1/72 Zoll) liefern. Bei
        Bildern wird das aus Pixelmasse und DPI berechnet -- so bekommt ein
        mit 600 dpi gescanntes A4-Blatt auch als PDF-Seite die Groesse von
        A4 und nicht irgendeine willkuerliche Pixelgroesse.

    EN: Return the physical page size in PDF points (1/72 inch). For images
        this is computed from pixel dimensions and DPI -- so a page scanned
        at 600 dpi ends up the correct physical page size (e.g. A4) in the
        resulting PDF instead of some arbitrary pixel-based size.
    """
    if source.kind == "pdf":
        with fitz.open(source.path) as doc:
            page = doc[source.index]
            return page.rect.width, page.rect.height
    with Image.open(source.path) as im:
        im.seek(source.index)
        dpi_x, dpi_y = bild_dpi(im)
        breite_pt = im.width / dpi_x * 72.0
        hoehe_pt = im.height / dpi_y * 72.0
        return breite_pt, hoehe_pt


def render_rgb(source: PageSource, max_dim: int) -> tuple[bytes, int, int]:
    """
    DE: Seite als rohe RGB-Bytes fuer eine Miniaturansicht rendern. Liefert
        (rgb_bytes, breite_px, hoehe_px); die laengere Kante wird auf
        max_dim begrenzt. PDF-Seiten werden ueber PyMuPDF gerastert, Bilder
        (auch einzelne TIFF-Frames) ueber Pillow.

    EN: Render a page as raw RGB bytes for a thumbnail preview. Returns
        (rgb_bytes, width_px, height_px); the longer edge is capped at
        max_dim. PDF pages are rasterized via PyMuPDF, images (including
        individual TIFF frames) via Pillow.
    """
    if source.kind == "pdf":
        with fitz.open(source.path) as doc:
            page = doc[source.index]
            skala = max_dim / max(page.rect.width, page.rect.height)
            skala = min(skala, 4.0)  # DE: Vergroesserung deckeln / EN: cap upscaling
            pix = page.get_pixmap(matrix=fitz.Matrix(skala, skala), colorspace=fitz.csRGB, alpha=False)
            return bytes(pix.samples), pix.width, pix.height
    with Image.open(source.path) as im:
        im.seek(source.index)
        rgb = im.convert("RGB")
        rgb.thumbnail((max_dim, max_dim), Image.LANCZOS)
        return rgb.tobytes(), rgb.width, rgb.height
