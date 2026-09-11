"""
DE: Registriert das Programm unter Windows in der Registry (nur fuer den
    aktuellen Nutzer, HKEY_CURRENT_USER -- keine Admin-Rechte noetig) als
    moegliche App fuer PDF- und Bilddateien. Ohne das taucht die App im
    Windows-Explorer-Kontextmenue "Öffnen mit" gar nicht erst auf bzw.
    wird nicht als Option gemerkt -- das macOS-Gegenstueck dazu ist
    CFBundleDocumentTypes im Info.plist (siehe build_mac.sh). Setzt NUR
    die App als moegliche Wahl ein, macht sie NICHT automatisch zur
    Standard-App -- das entscheidet der Nutzer wie ueblich selbst ueber
    "Öffnen mit" -> "Diese App immer verwenden" im Explorer.

    ACHTUNG: Ungetestet auf echtem Windows (dieses Projekt wird nur auf
    macOS entwickelt/getestet, siehe pdfkrams/info.py bzw. den Hinweis
    im Über-Dialog) -- bei Problemen bitte an
    telefonmann@telefonanleitungen.de melden. Deshalb besonders defensiv:
    registrieren() faengt JEDEN Fehler ab, ein Fehlschlagen hier darf den
    Programmstart nie verhindern.

EN: Registers the program in the Windows registry (current-user only,
    HKEY_CURRENT_USER -- no admin rights needed) as a possible app for
    PDF and image files. Without this the app doesn't show up at all in
    Windows Explorer's "Open with" context menu resp. isn't remembered as
    an option -- the macOS counterpart is CFBundleDocumentTypes in
    Info.plist (see build_mac.sh). Only registers the app as a possible
    choice, does NOT automatically make it the default -- the user still
    decides that themselves as usual via "Open with" -> "Always use this
    app" in Explorer.

    WARNING: Untested on real Windows (this project is only developed/
    tested on macOS, see pdfkrams/info.py resp. the About dialog note) --
    please report problems to telefonmann@telefonanleitungen.de. Hence
    extra defensive: registrieren() catches ANY error, a failure here
    must never prevent the program from starting.
"""

from __future__ import annotations

import sys

_ENDUNGEN = (".pdf", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".png")
_APP_ID = "MathiasKleinesPDFWerkzeug"


def registrieren() -> None:
    """
    DE: Traegt die Registry-Eintraege ein -- nur wenn tatsaechlich unter
        Windows als gebaute exe ausgefuehrt (nicht im Entwicklungsbetrieb
        z. B. via `python -m pdfkrams.main`, dort zeigt sys.executable
        auf den Python-Interpreter statt auf die eigene exe). Wird bei
        jedem Start aufgerufen -- das erneute Schreiben derselben Werte
        ist guenstig und stellt sicher, dass sich z. B. ein geaenderter
        Installationspfad der exe automatisch aktualisiert.
    EN: Writes the registry entries -- only when actually running as a
        built exe on Windows (not in development, e.g. via
        `python -m pdfkrams.main`, where sys.executable points at the
        Python interpreter instead of the app's own exe). Called on
        every startup -- rewriting the same values is cheap and ensures
        e.g. a changed installation path of the exe gets picked up
        automatically.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        _registrieren_impl()
    except Exception:  # noqa: BLE001 -- Komfort-Feature, darf den Start nie verhindern
        pass


def _registrieren_impl() -> None:
    import winreg

    exe_pfad = sys.executable
    basis = rf"Software\Classes\Applications\{_APP_ID}.exe"

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, basis) as schluessel:
        winreg.SetValueEx(schluessel, "FriendlyAppName", 0, winreg.REG_SZ, "Mathias kleines PDF-Werkzeug")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, basis + r"\shell\open\command") as schluessel:
        winreg.SetValueEx(schluessel, "", 0, winreg.REG_SZ, f'"{exe_pfad}" "%1"')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, basis + r"\SupportedTypes") as schluessel:
        for endung in _ENDUNGEN:
            winreg.SetValueEx(schluessel, endung, 0, winreg.REG_SZ, "")

    # DE: Zusaetzlich je Endung in die OpenWithList eintragen -- auf
    #     manchen Windows-Versionen reicht SupportedTypes allein nicht,
    #     damit die App im Kontextmenue "Öffnen mit" auftaucht.
    # EN: Also register per extension in OpenWithList -- on some Windows
    #     versions SupportedTypes alone isn't enough for the app to show
    #     up in the "Open with" context menu.
    for endung in _ENDUNGEN:
        pfad = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{endung}\OpenWithList"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, pfad) as schluessel:
            winreg.SetValueEx(schluessel, f"{_APP_ID}.exe", 0, winreg.REG_SZ, "")
