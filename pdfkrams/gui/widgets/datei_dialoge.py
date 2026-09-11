"""
DE: Duenne Wrapper um QFileDialog.getOpenFileName(s)/getSaveFileName/
    getExistingDirectory, die sich zusaetzlich den zuletzt verwendeten
    Ordner merken (siehe einstellungen.letzter_ordner) und ihn beim
    naechsten Aufruf -- auch aus einem ganz anderen Werkzeug -- wieder als
    Startordner vorschlagen. Ohne das faengt jeder Dialog immer im
    Vorgabe-Ordner des Betriebssystems an, was bei tief verschachtelten
    Projektordnern laestig ist.

EN: Thin wrappers around QFileDialog.getOpenFileName(s)/getSaveFileName/
    getExistingDirectory that additionally remember the last-used folder
    (see einstellungen.letzter_ordner) and suggest it again as the
    starting folder on the next call -- even from a completely different
    tool. Without this, every dialog always starts in the OS's default
    folder, which is annoying with deeply nested project folders.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from pdfkrams.einstellungen import einstellungen


def _start_pfad(dateiname_vorschlag: str = "") -> str:
    ordner = einstellungen.letzter_ordner()
    if not ordner:
        return dateiname_vorschlag
    return str(Path(ordner) / dateiname_vorschlag) if dateiname_vorschlag else ordner


def oeffnen_dialog(parent: QWidget, titel: str, filter_text: str) -> list[Path]:
    """DE: Mehrere Dateien zum Oeffnen auswaehlen.
    EN: Choose multiple files to open."""
    pfade, _ = QFileDialog.getOpenFileNames(parent, titel, _start_pfad(), filter_text)
    if pfade:
        einstellungen.letzter_ordner_setzen(str(Path(pfade[0]).parent))
    return [Path(p) for p in pfade]


def einzeln_oeffnen_dialog(parent: QWidget, titel: str, filter_text: str) -> Path | None:
    """DE: Eine einzelne Datei zum Oeffnen auswaehlen.
    EN: Choose a single file to open."""
    pfad, _ = QFileDialog.getOpenFileName(parent, titel, _start_pfad(), filter_text)
    if not pfad:
        return None
    einstellungen.letzter_ordner_setzen(str(Path(pfad).parent))
    return Path(pfad)


def speichern_dialog(parent: QWidget, titel: str, dateiname_vorschlag: str, filter_text: str) -> Path | None:
    """DE: Zielpfad zum Speichern auswaehlen.
    EN: Choose a target path to save to."""
    ziel, _ = QFileDialog.getSaveFileName(parent, titel, _start_pfad(dateiname_vorschlag), filter_text)
    if not ziel:
        return None
    einstellungen.letzter_ordner_setzen(str(Path(ziel).parent))
    return Path(ziel)


def ordner_dialog(parent: QWidget, titel: str) -> Path | None:
    """DE: Einen Ordner auswaehlen (z. B. als Zielordner).
    EN: Choose a folder (e.g. as a target folder)."""
    ordner = QFileDialog.getExistingDirectory(parent, titel, _start_pfad())
    if not ordner:
        return None
    einstellungen.letzter_ordner_setzen(ordner)
    return Path(ordner)
