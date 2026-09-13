"""
DE: Persistente Anwendungseinstellungen (Sprache, Maßeinheit,
    Datumsformat, Standard-Anbieter, Schwärzungsfarbe) -- über
    QSettings gespeichert (landet automatisch am für macOS/Windows
    jeweils üblichen Ort), an genau dieser Stelle zentral gebündelt.

    Bewusst NICHT aus der Betriebssystem-Sprache/-Region abgeleitet: die
    zu bearbeitenden PDF-Dateien können aus jedem Land stammen, völlig
    unabhängig davon, wie der Rechner selbst eingestellt ist -- ein
    deutscher Nutzer bearbeitet z. B. ganz normal ein US-Letter-Dokument.
    Deshalb hier ausschließlich manuelle Umschaltung, nichts wird
    automatisch anhand der Systemsprache vorbelegt.

EN: Persistent application settings (language, measurement unit, date
    format, default provider, redaction color) --
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

from datetime import date

from PySide6.QtCore import QObject, QSettings, Signal

from pdfkrams.core import schwaerzung as _schwaerzung
from pdfkrams.info import ANBIETER

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

# DE: Datumsformat fuer das Releasedatum im Werkzeug "Metadaten
#     bearbeiten" (Dateiname-Vorschlag + Stichwoerter) -- Anzeigename ->
#     strftime-Muster. Bewusst als feste Auswahl statt freier
#     strftime-Eingabe, um Tippfehler zu vermeiden.
# EN: Date format for the release date in the "Edit metadata" tool
#     (filename suggestion + keywords) -- display name -> strftime
#     pattern. Deliberately a fixed choice instead of free-form strftime
#     input, to avoid typos.
DATUMSFORMATE: dict[str, str] = {
    "jj-mm": "JJ-MM (z. B. 26-09)",
    "jjjj-mm-tt": "JJJJ-MM-TT (z. B. 2026-09-10)",
    "tt.mm.jjjj": "TT.MM.JJJJ (z. B. 10.09.2026)",
}
_DATUMSFORMAT_MUSTER: dict[str, str] = {
    "jj-mm": "%y-%m",
    "jjjj-mm-tt": "%Y-%m-%d",
    "tt.mm.jjjj": "%d.%m.%Y",
}
STANDARD_DATUMSFORMAT = "jj-mm"

# DE: Farbe fuers Schwaerzen-Werkzeug, als "#RRGGBB"-Hexcode -- Standard
#     Schwarz, wie in Akten/Verwaltungsschriftgut ueblich.
# EN: Color for the redaction tool, as a "#RRGGBB" hex code -- defaults
#     to black, as customary in case files/administrative records.
STANDARD_SCHWAERZUNGSFARBE = "#000000"


def _hex_zu_rgb(hex_code: str) -> tuple[int, int, int]:
    hex_code = hex_code.lstrip("#")
    return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)


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
    datumsformatGeaendert = Signal(str)
    anbieterStandardGeaendert = Signal(str)
    schwaerzungsfarbeGeaendert = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings(_ORGANISATION, _ANWENDUNG)
        # DE: core/schwaerzung.py bei Start auf die zuletzt gespeicherte
        #     Farbe bringen (das core-Modul selbst kennt QSettings nicht).
        # EN: Bring core/schwaerzung.py up to the last saved color on
        #     startup (the core module itself doesn't know about QSettings).
        _schwaerzung.farbe_setzen(_hex_zu_rgb(self.schwaerzungsfarbe()))

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

    def datumsformat(self) -> str:
        wert = self._settings.value("datumsformat", STANDARD_DATUMSFORMAT)
        return wert if wert in DATUMSFORMATE else STANDARD_DATUMSFORMAT

    def datumsformat_setzen(self, code: str) -> None:
        if code not in DATUMSFORMATE or code == self.datumsformat():
            return
        self._settings.setValue("datumsformat", code)
        self.datumsformatGeaendert.emit(code)

    def datum_formatieren(self, datum: date) -> str:
        """DE: Formatiert ein Datum nach dem aktuell eingestellten
            Datumsformat (siehe DATUMSFORMATE).
        EN: Formats a date according to the currently configured date
            format (see DATUMSFORMATE)."""
        return datum.strftime(_DATUMSFORMAT_MUSTER[self.datumsformat()])

    def anbieter_standard(self) -> str:
        """DE: In den Einstellungen fest hinterlegter Standard-Anbieter
            (z. B. "Telefonanleitungen.de") -- wird beim Metadaten-
            Werkzeug vorbelegt, solange fuer das aktuelle Dokument noch
            kein eigener Anbieter eingetragen wurde. Voreingestellt auf
            ANBIETER aus info.py, aber jederzeit anpassbar/loeschbar.
        EN: A default provider fixed in Preferences (e.g.
            "Telefonanleitungen.de") -- prefills the metadata tool as
            long as the current document hasn't had its own provider
            entered yet. Defaults to ANBIETER from info.py, but can be
            changed/cleared at any time."""
        wert = self._settings.value("anbieterStandard", None)
        return ANBIETER if wert is None else wert

    def anbieter_standard_setzen(self, text: str) -> None:
        if text == self.anbieter_standard():
            return
        self._settings.setValue("anbieterStandard", text)
        self.anbieterStandardGeaendert.emit(text)

    def anbieter_letzter(self) -> str:
        """DE: Zuletzt im Metadaten-Werkzeug eingetragener Anbieter --
            Rueckfallebene, falls kein Standard-Anbieter in den
            Einstellungen hinterlegt ist (siehe anbieter_standard).
        EN: The provider most recently entered in the metadata tool --
            fallback if no default provider is set in Preferences (see
            anbieter_standard)."""
        return self._settings.value("anbieterLetzter", "")

    def anbieter_letzter_setzen(self, text: str) -> None:
        self._settings.setValue("anbieterLetzter", text)

    def schwaerzungsfarbe(self) -> str:
        """DE: Aktuelle Schwaerzungsfarbe als "#RRGGBB"-Hexcode.
        EN: Current redaction color as a "#RRGGBB" hex code."""
        return self._settings.value("schwaerzungsfarbe", STANDARD_SCHWAERZUNGSFARBE)

    def schwaerzungsfarbe_setzen(self, hex_code: str) -> None:
        if hex_code == self.schwaerzungsfarbe():
            return
        self._settings.setValue("schwaerzungsfarbe", hex_code)
        _schwaerzung.farbe_setzen(_hex_zu_rgb(hex_code))
        self.schwaerzungsfarbeGeaendert.emit(hex_code)

    def letzter_ordner(self) -> str:
        """DE: Ordner, in dem der Nutzer zuletzt eine Datei geoeffnet oder
            gespeichert hat -- als Startordner fuer den naechsten Datei-
            dialog, ganz gleich in welchem Werkzeug (siehe
            gui/widgets/datei_dialoge.py). Leerer String, falls noch nie
            etwas gespeichert wurde (QFileDialog faellt dann auf seinen
            eigenen Standardordner zurueck).
        EN: Folder the user most recently opened or saved a file in -- used
            as the starting folder for the next file dialog, in ANY tool
            (see gui/widgets/datei_dialoge.py). Empty string if nothing has
            been saved yet (QFileDialog then falls back to its own default
            folder)."""
        return self._settings.value("letzterOrdner", "")

    def letzter_ordner_setzen(self, pfad: str) -> None:
        self._settings.setValue("letzterOrdner", pfad)

    def splitter_groessen(self) -> list[int] | None:
        """DE: Zuletzt gemerkte Spaltenbreiten des Hauptfenster-Splitters
            (Werkzeugliste/Dateiliste/Werkzeug-Bereich), oder None, falls
            noch nie gespeichert.
        EN: Last remembered column widths of the main window's splitter
            (tool list/file list/tool area), or None if never saved."""
        wert = self._settings.value("splitterGroessen", None)
        return [int(w) for w in wert] if wert else None

    def splitter_groessen_setzen(self, groessen: list[int]) -> None:
        self._settings.setValue("splitterGroessen", groessen)

    def werkzeugliste_sichtbar(self) -> bool:
        """DE: Ob die linke Werkzeugliste eingeblendet ist (F4 bzw.
            Ansicht-Menue) -- ueber Programmstarts hinweg gemerkt.
        EN: Whether the left tool list is shown (F4 resp. the View menu)
            -- remembered across program launches."""
        wert = self._settings.value("werkzeuglisteSichtbar", True)
        return wert in (True, "true", "1", 1)

    def werkzeugliste_sichtbar_setzen(self, sichtbar: bool) -> None:
        self._settings.setValue("werkzeuglisteSichtbar", sichtbar)

    def rotationslinien_farbe(self) -> str:
        """DE: Farbe der Referenzlinien im Dreh-Werkzeug, als Hex-String
            (z. B. "#ff4646") -- ueber Programmstarts hinweg gemerkt, damit
            eine einmal gewaehlte, zur eigenen Seitenfarbe passende Farbe
            nicht bei jedem Start neu gesetzt werden muss.
        EN: Color of the reference lines in the rotate tool, as a hex
            string (e.g. "#ff4646") -- remembered across program launches,
            so a color once chosen to match one's own page color doesn't
            need to be reset on every start."""
        return str(self._settings.value("rotationslinienFarbe", "#ff4646"))

    def rotationslinien_farbe_setzen(self, farbe_hex: str) -> None:
        self._settings.setValue("rotationslinienFarbe", farbe_hex)

    def passwort_log(self) -> list[dict]:
        """DE: Liste vergebener PDF-Passwoerter (siehe core/passwort_log.py) --
            als Klartext in QSettings abgelegt, bewusst nicht verschluesselt
            (siehe passwortschutz.py's Docstring).
        EN: List of PDF passwords that have been set (see
            core/passwort_log.py) -- stored as plaintext in QSettings,
            deliberately unencrypted (see passwortschutz.py's docstring)."""
        wert = self._settings.value("passwortLog", [])
        return wert if isinstance(wert, list) else []

    def passwort_log_setzen(self, eintraege: list[dict]) -> None:
        self._settings.setValue("passwortLog", eintraege)


# DE: Eine einzige, geteilte Instanz fuer die ganze App -- wie bei
#     pdfkrams/info.py bewusst als Modul-Singleton statt Dependency
#     Injection, da es sich um globale, seltene Einstellungen handelt.
# EN: One single shared instance for the whole app -- like
#     pdfkrams/info.py, deliberately a module-level singleton instead of
#     dependency injection, since these are global, infrequently-changed
#     settings.
einstellungen = _Einstellungen()
