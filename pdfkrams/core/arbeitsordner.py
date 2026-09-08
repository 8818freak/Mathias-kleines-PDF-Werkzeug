"""
DE: Gemeinsamer temporaerer Ordner fuer Zwischenergebnisse, die innerhalb
    der App weiterverarbeitet werden sollen (z. B. materialisierte
    Teilungen, siehe export_dateien.materialisiere_teilung). Wird beim
    ersten Zugriff angelegt und beim Beenden des Programms automatisch
    aufgeraeumt -- anders als beim regulaeren Export handelt es sich hier
    nicht um Dateien, die der Nutzer bewusst behalten will.

EN: Shared temporary folder for intermediate results meant for continued
    in-app processing (e.g. materialized splits, see
    export_dateien.materialisiere_teilung). Created on first access and
    cleaned up automatically when the program exits -- unlike a regular
    export, these aren't files the user deliberately wants to keep.
"""

from __future__ import annotations

import atexit
import tempfile
from pathlib import Path

_verzeichnis: tempfile.TemporaryDirectory | None = None


def pfad() -> Path:
    """DE: Pfad des Arbeitsordners liefern, ihn beim ersten Aufruf anlegen.
    EN: Return the working folder's path, creating it on first call."""
    global _verzeichnis
    if _verzeichnis is None:
        _verzeichnis = tempfile.TemporaryDirectory(prefix="pdfkrams_")
        atexit.register(_verzeichnis.cleanup)
    return Path(_verzeichnis.name)
