"""
DE: Duenne Wrapper um QFileDialog.getOpenFileName(s)/getSaveFileName/
    getExistingDirectory, die zwei Dinge zusaetzlich erledigen:

    1. Sie merken sich den zuletzt verwendeten Ordner (siehe
       einstellungen.letzter_ordner) und schlagen ihn beim naechsten
       Aufruf -- auch aus einem ganz anderen Werkzeug -- wieder als
       Startordner vor. Ohne das faengt jeder Dialog immer im
       Vorgabe-Ordner des Betriebssystems an, was bei tief
       verschachtelten Projektordnern laestig ist.

    2. Sie erzwingen Qt's EIGENEN Dialog statt des nativen macOS-Panels
       (DontUseNativeDialog). Grund: das native Panel liegt komplett
       ausserhalb der Qt-Widget-Hierarchie -- Cmd+V/C/X/A im
       Dateinamen-Feld dort liess sich dadurch grundsaetzlich nicht
       zuverlaessig zum Laufen bringen (siehe die Cut/Copy/Paste/
       Select-All-Aktionen in main_window.py: sie wirken nur auf
       QApplication.focusWidget(), was ein natives Feld nie liefert).
       Schlimmer noch: sobald diese Aktionen im Bearbeiten-Menue
       registriert sind, faengt macOS Cmd+V dafuer ab, OHNE es ans
       native Feld weiterzureichen -- das Kuerzel wirkte dadurch
       "irgendwie", aenderte den Text aber nicht. Qt's eigener Dialog
       sieht zwar nicht ganz so nativ aus, garantiert aber, dass die
       Tastenkuerzel tatsaechlich funktionieren.

EN: Thin wrappers around QFileDialog.getOpenFileName(s)/getSaveFileName/
    getExistingDirectory that additionally do two things:

    1. They remember the last-used folder (see
       einstellungen.letzter_ordner) and suggest it again as the
       starting folder on the next call -- even from a completely
       different tool. Without this, every dialog always starts in the
       OS's default folder, which is annoying with deeply nested
       project folders.

    2. They force Qt's OWN dialog instead of the native macOS panel
       (DontUseNativeDialog). Reason: the native panel lives entirely
       outside the Qt widget hierarchy -- Cmd+V/C/X/A in its filename
       field could therefore never be made reliably to work (see the
       Cut/Copy/Paste/Select-All actions in main_window.py: they only
       act on QApplication.focusWidget(), which a native field never
       is). Worse, once those actions are registered in the Edit menu,
       macOS intercepts Cmd+V for them WITHOUT forwarding it to the
       native field -- the shortcut then appeared to do "something"
       without actually changing the text. Qt's own dialog looks a
       little less native, but guarantees the shortcuts actually work.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from pdfkrams.einstellungen import einstellungen

# DE: Siehe Begruendung oben -- an allen vier Dialogen unten verwendet.
# EN: See the rationale above -- used on all four dialogs below.
_OPTIONEN = QFileDialog.Option.DontUseNativeDialog


def _start_pfad(dateiname_vorschlag: str = "") -> str:
    ordner = einstellungen.letzter_ordner()
    if not ordner:
        return dateiname_vorschlag
    return str(Path(ordner) / dateiname_vorschlag) if dateiname_vorschlag else ordner


def oeffnen_dialog(parent: QWidget, titel: str, filter_text: str) -> list[Path]:
    """DE: Mehrere Dateien zum Oeffnen auswaehlen.
    EN: Choose multiple files to open."""
    pfade, _ = QFileDialog.getOpenFileNames(parent, titel, _start_pfad(), filter_text, options=_OPTIONEN)
    if pfade:
        einstellungen.letzter_ordner_setzen(str(Path(pfade[0]).parent))
    return [Path(p) for p in pfade]


def einzeln_oeffnen_dialog(parent: QWidget, titel: str, filter_text: str) -> Path | None:
    """DE: Eine einzelne Datei zum Oeffnen auswaehlen.
    EN: Choose a single file to open."""
    pfad, _ = QFileDialog.getOpenFileName(parent, titel, _start_pfad(), filter_text, options=_OPTIONEN)
    if not pfad:
        return None
    einstellungen.letzter_ordner_setzen(str(Path(pfad).parent))
    return Path(pfad)


def speichern_dialog(parent: QWidget, titel: str, dateiname_vorschlag: str, filter_text: str) -> Path | None:
    """DE: Zielpfad zum Speichern auswaehlen.
    EN: Choose a target path to save to."""
    ziel, _ = QFileDialog.getSaveFileName(parent, titel, _start_pfad(dateiname_vorschlag), filter_text, options=_OPTIONEN)
    if not ziel:
        return None
    einstellungen.letzter_ordner_setzen(str(Path(ziel).parent))
    return Path(ziel)


def ordner_dialog(parent: QWidget, titel: str) -> Path | None:
    """DE: Einen Ordner auswaehlen (z. B. als Zielordner).
    EN: Choose a folder (e.g. as a target folder)."""
    ordner = QFileDialog.getExistingDirectory(parent, titel, _start_pfad(), options=_OPTIONEN)
    if not ordner:
        return None
    einstellungen.letzter_ordner_setzen(ordner)
    return Path(ordner)
