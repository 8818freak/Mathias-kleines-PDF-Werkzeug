"""
DE: Ein bestehendes PDF nachtraeglich mit den strukturellen Bestandteilen
    fuer PDF/A-2b versehen: ein eingebettetes sRGB-Farbprofil
    (OutputIntent) und XMP-Metadaten mit der PDF/A-Kennzeichnung
    (pdfaid:part=2, pdfaid:conformance=B). Die Seiten dieser App sind
    reine Bildseiten ohne Schriften, Transparenz oder Verschluesselung --
    die uebrigen, kniffligeren Anforderungen von PDF/A (eingebettete
    Schriften, keine Verschluesselung, kein LZW) sind dadurch bereits
    von selbst erfuellt.

    Diese Funktion setzt die ueblichen, von Software erkannten Kennzeichen,
    ist aber KEIN Ersatz fuer eine echte Validierung. Fuer eine
    verbindliche Pruefung ein dediziertes Werkzeug wie veraPDF
    gegenlaufen lassen.

EN: Retrofits an existing PDF with the structural pieces required for
    PDF/A-2b: an embedded sRGB color profile (OutputIntent) and XMP
    metadata declaring PDF/A conformance (pdfaid:part=2,
    pdfaid:conformance=B). This app's pages are plain image pages without
    fonts, transparency, or encryption -- so PDF/A's other, trickier
    requirements (embedded fonts, no encryption, no LZW) are already
    satisfied by construction.

    This function sets the usual markers recognized by software, but is
    NOT a substitute for real validation. For a binding check, run a
    dedicated tool like veraPDF against the result.
"""

from __future__ import annotations

from pathlib import Path

import pikepdf
from pikepdf import Array, Dictionary, Name
from PIL import ImageCms

from ..info import pdf_metadaten_eintrag


def _srgb_icc_profil() -> bytes:
    """DE: sRGB-Farbprofil im Arbeitsspeicher erzeugen (kein externer Bedarf).
    EN: Generate an sRGB color profile in memory (no external dependency)."""
    profil = ImageCms.createProfile("sRGB")
    return ImageCms.ImageCmsProfile(profil).tobytes()


def als_pdfa_markieren(quelle: Path, ziel: Path, titel: str = "") -> None:
    """
    DE: `quelle` oeffnen, OutputIntent (sRGB) und PDF/A-2b-XMP-Metadaten
        ergaenzen und als `ziel` speichern.

    EN: Open `quelle`, add an sRGB OutputIntent and PDF/A-2b XMP metadata,
        and save as `ziel`.
    """
    with pikepdf.open(quelle) as pdf:
        icc_stream = pdf.make_stream(_srgb_icc_profil())
        icc_stream["/N"] = 3
        icc_stream["/Alternate"] = Name.DeviceRGB

        output_intent = pdf.make_indirect(Dictionary(
            Type=Name.OutputIntent,
            S=Name.GTS_PDFA1,
            OutputConditionIdentifier="sRGB IEC61966-2.1",
            Info="sRGB IEC61966-2.1",
            DestOutputProfile=icc_stream,
        ))
        if "/OutputIntents" in pdf.Root:
            pdf.Root.OutputIntents.append(output_intent)
        else:
            pdf.Root.OutputIntents = Array([output_intent])

        eintrag = pdf_metadaten_eintrag()
        pdf.docinfo["/Producer"] = eintrag
        pdf.docinfo["/Creator"] = eintrag

        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta["pdfaid:part"] = "2"
            meta["pdfaid:conformance"] = "B"
            meta["xmp:CreatorTool"] = eintrag
            if titel:
                meta["dc:title"] = titel

        pdf.save(ziel)
