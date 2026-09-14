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

from PySide6.QtWidgets import QFileDialog, QLineEdit, QWidget

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
    """
    DE: Zielpfad zum Speichern auswaehlen. Anders als die uebrigen
        Dialoge oben eine echte QFileDialog-Instanz statt der statischen
        getSaveFileName()-Kurzform -- nur so laesst sich das Dateinamen-
        Feld nachtraeglich anfassen, um zwei Dinge nachzubilden, die
        macOS' natives Speichern-Panel von sich aus kann, Qt's eigenes
        (siehe _OPTIONEN oben) aber nicht: 1. beim Anklicken einer Datei
        in der Liste wird nur ihr NAME markiert, nicht die Endung -- Pfeil
        Rechts springt ans Ende des Namens (vor die Endung), Tippen
        ueberschreibt nur den Namen. 2. Endung automatisch ergaenzen,
        falls sie durch das Ueberschreiben verloren ging (setDefaultSuffix
        -- greift nur, wenn der eingegebene Name GAR KEINE Endung mehr hat,
        nicht wenn absichtlich eine andere gewaehlt wurde).
    EN: Choose a target path to save to. Unlike the other dialogs above,
        a real QFileDialog instance instead of the static
        getSaveFileName() convenience form -- only that allows reaching
        into the filename field afterward, to reproduce two things
        macOS' native Save panel does on its own but Qt's own dialog
        (see _OPTIONEN above) doesn't: 1. clicking a file in the list
        selects only its NAME, not the extension -- Right Arrow jumps to
        the end of the name (before the extension), typing overwrites
        only the name. 2. auto-append the extension if it got lost by
        overwriting (setDefaultSuffix -- only kicks in when the entered
        name has NO extension at all left, not when a different one was
        deliberately chosen).
    """
    dialog = QFileDialog(parent, titel, _start_pfad(dateiname_vorschlag), filter_text)
    dialog.setOptions(_OPTIONEN)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    endung = Path(dateiname_vorschlag).suffix.lstrip(".")
    if endung:
        dialog.setDefaultSuffix(endung)
    dialog.selectFile(dateiname_vorschlag)

    feld = dialog.findChild(QLineEdit, "fileNameEdit")
    if feld is not None:
        def _nur_namen_markieren(pfad: str) -> None:
            name = Path(pfad).name
            # DE: Nur eingreifen, wenn das Feld GENAU diesen Dateinamen
            #     zeigt -- ohne diese Pruefung wuerde eine Markierung
            #     ueberschrieben, die der Nutzer inzwischen selbst per
            #     Hand gesetzt hat.
            # EN: Only intervene if the field shows EXACTLY this
            #     filename -- without this check, a selection the user
            #     has since set by hand themselves would be overwritten.
            if feld.text() != name:
                return
            stamm = Path(pfad).stem
            if stamm:
                feld.setSelection(0, len(stamm))
        dialog.currentChanged.connect(_nur_namen_markieren)
        _nur_namen_markieren(dateiname_vorschlag)

    if dialog.exec() != QFileDialog.DialogCode.Accepted:
        return None
    ausgewaehlt = dialog.selectedFiles()
    if not ausgewaehlt:
        return None
    ziel = ausgewaehlt[0]
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
