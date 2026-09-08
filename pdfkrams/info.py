"""
DE: Zentrale Angaben zum Programm selbst -- Name, Version, Anbieter,
    Website. An genau dieser Stelle gepflegt, damit sie sowohl im
    "Über"-Dialog als auch in den Metadaten jeder von diesem Programm
    erzeugten PDF-Datei konsistent auftauchen.

EN: Central facts about the program itself -- name, version, provider,
    website. Maintained in exactly this one place so they show up
    consistently both in the "About" dialog and in the metadata of every
    PDF file this program produces.
"""

from __future__ import annotations

PROGRAMMNAME = "Mathias' kleines PDF-Werkzeug"
VERSION = "1.0"
ANBIETER = "Telefonanleitungen.de"
WEBSITE = "https://www.telefonanleitungen.de"


def voller_programmname() -> str:
    """DE: Name samt Version, z. B. fuer Fenstertitel/Metadaten.
    EN: Name including version, e.g. for window titles/metadata."""
    return f"{PROGRAMMNAME} {VERSION}"


def pdf_metadaten_eintrag() -> str:
    """
    DE: Einzeiliger Text fuer die PDF-Felder Creator/Producer -- taucht so
        in Finder-Vorschau, Acrobat-Dokumenteigenschaften etc. auf.
    EN: Single-line text for the PDF Creator/Producer fields -- shows up
        this way in Finder preview, Acrobat document properties, etc.
    """
    return f"{voller_programmname()} -- kostenlos bereitgestellt von {ANBIETER} -- {WEBSITE}"


def pdf_metadaten() -> dict[str, str]:
    """
    DE: Fertiges Dict fuer fitz.Document.set_metadata() -- setzt Creator
        und Producer, laesst alle anderen Felder (Titel etc.) unangetastet.
    EN: Ready-made dict for fitz.Document.set_metadata() -- sets Creator
        and Producer, leaves every other field (title etc.) untouched.
    """
    eintrag = pdf_metadaten_eintrag()
    return {"creator": eintrag, "producer": eintrag}
