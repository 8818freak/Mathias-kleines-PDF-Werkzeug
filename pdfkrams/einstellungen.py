"""
DE: Persistente Anwendungseinstellungen (Sprache, Maßeinheit) -- über
    QSettings gespeichert (landet automatisch am für macOS/Windows
    jeweils üblichen Ort), an genau dieser Stelle zentral gebündelt.

    Bewusst NICHT aus der Betriebssystem-Sprache/-Region abgeleitet: die
    zu bearbeitenden PDF-Dateien können aus jedem Land stammen, völlig
    unabhängig davon, wie der Rechner selbst eingestellt ist -- ein
    deutscher Nutzer bearbeitet z. B. ganz normal ein US-Letter-Dokument.
    Deshalb hier ausschließlich manuelle Umschaltung, nichts wird
    automatisch anhand der Systemsprache vorbelegt.

EN: Persistent application settings (language, measurement unit) --
    stored via QSettings (lands automatically wherever macOS/Windows
    conventionally keep such data), bundled centrally in exactly this
    place.

    Deliberately NOT derived from the OS language/region: the PDF files
    being processed can originate from any country, entirely independent
    of how the computer itself is configured -- e.g. a German user might
    perfectly normally be working on a US Letter document. Hence purely
    manual switching here, nothing is auto-selected from the system
    language.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal

_ORGANISATION = "Telefonanleitungen.de"
_ANWENDUNG = "MathiasKleinesPDFWerkzeug"

# DE: Sprachcode -> Anzeigename. Weitere Sprachen spaeter einfach
#     ergaenzen (siehe pdfkrams/i18n.py) -- an dieser Liste allein aendert
#     sich dafuer nichts weiter.
# EN: Language code -> display name. Add further languages later simply
#     by extending this (see pdfkrams/i18n.py) -- nothing else about this
#     list needs to change for that.
SPRACHEN: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
}
STANDARD_SPRACHE = "de"

MASSEINHEITEN: dict[str, str] = {
    "mm": "Millimeter (mm)",
    "in": "Zoll (in)",
}
STANDARD_MASSEINHEIT = "mm"


class _Einstellungen(QObject):
    """
    DE: Singleton fuer die laufzeitweiten Einstellungen. Aenderungen
        werden sofort in QSettings gespeichert und ueber Signale an alle
        interessierten Werkzeuge gemeldet (z. B. damit das Seitenmass-
        Werkzeug live auf eine neue Masseinheit umschaltet, ohne dass ein
        Neustart noetig ist).
    EN: Singleton for the runtime-wide settings. Changes are saved to
        QSettings immediately and broadcast via signals to any
        interested tool (e.g. so the page-size tool switches to a new
        measurement unit live, without needing a restart).
    """

    spracheGeaendert = Signal(str)
    masseinheitGeaendert = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings(_ORGANISATION, _ANWENDUNG)

    def sprache(self) -> str:
        wert = self._settings.value("sprache", STANDARD_SPRACHE)
        return wert if wert in SPRACHEN else STANDARD_SPRACHE

    def sprache_setzen(self, code: str) -> None:
        if code not in SPRACHEN or code == self.sprache():
            return
        self._settings.setValue("sprache", code)
        self.spracheGeaendert.emit(code)

    def masseinheit(self) -> str:
        wert = self._settings.value("masseinheit", STANDARD_MASSEINHEIT)
        return wert if wert in MASSEINHEITEN else STANDARD_MASSEINHEIT

    def masseinheit_setzen(self, code: str) -> None:
        if code not in MASSEINHEITEN or code == self.masseinheit():
            return
        self._settings.setValue("masseinheit", code)
        self.masseinheitGeaendert.emit(code)


# DE: Eine einzige, geteilte Instanz fuer die ganze App -- wie bei
#     pdfkrams/info.py bewusst als Modul-Singleton statt Dependency
#     Injection, da es sich um globale, seltene Einstellungen handelt.
# EN: One single shared instance for the whole app -- like
#     pdfkrams/info.py, deliberately a module-level singleton instead of
#     dependency injection, since these are global, infrequently-changed
#     settings.
einstellungen = _Einstellungen()
