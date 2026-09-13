"""
DE: Berechnungen fuer PDF-native Seitenbeschriftungen (page labels) -- die
    kleine Nummer/Bezeichnung, die Programme wie Acrobat statt der reinen
    Blattposition im Seiten-Navigator anzeigen (z. B. ein Umschlag in
    roemischen Ziffern I-IV vor einem in arabischen Ziffern 1-N
    durchnummerierten Buchblock). Siehe core/document.py's WorkingPage-
    Felder beschriftung_stil/_praefix/_start fuer die Datenhaltung je
    Seite und gui/tools/seitenbeschriftung_tool.py fuer die Bedienung.

EN: Calculations for PDF-native page labels -- the small number/label
    that programs like Acrobat show in the page navigator instead of the
    raw sheet position (e.g. a cover in roman numerals I-IV before a book
    block numbered 1-N in arabic numerals). See core/document.py's
    WorkingPage fields beschriftung_stil/_praefix/_start for the per-page
    data and gui/tools/seitenbeschriftung_tool.py for the UI.
"""

from __future__ import annotations

from dataclasses import dataclass

from .document import WorkingPage

# DE: Gueltige Stil-Codes (identisch mit dem PDF-Standard/PyMuPDF) samt
#     Anzeigename fuer die Oberflaeche, in sinnvoller Auswahl-Reihenfolge.
# EN: Valid style codes (identical to the PDF standard/PyMuPDF) with a
#     display name for the UI, in a sensible selection order.
STILE: dict[str, str] = {
    "D": "1, 2, 3, …",
    "R": "I, II, III, …",
    "r": "i, ii, iii, …",
    "A": "A, B, C, …",
    "a": "a, b, c, …",
    "": "Kein (nur Präfix)",
}


def _formatiert(stil: str, zahl: int) -> str:
    """DE: Rein numerischen Teil einer Beschriftung fuer die Vorschau
        darstellen -- nur fuer die Anzeige, nicht fuer den PDF-Export
        (das uebernimmt PyMuPDF/der PDF-Betrachter selbst).
    EN: Render just the numeric part of a label for the preview --
        display only, not used for the PDF export (PyMuPDF/the PDF
        viewer handle that themselves)."""
    if stil == "D" or stil not in ("R", "r", "A", "a"):
        return str(zahl)
    if stil in ("R", "r"):
        werte = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                 (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
        rest, roemisch = max(1, zahl), ""
        for wert, zeichen in werte:
            while rest >= wert:
                roemisch += zeichen
                rest -= wert
        return roemisch if stil == "R" else roemisch.lower()
    # DE: Buchstaben-Stil: 1=A, 2=B, ..., 26=Z, 27=AA, 28=AB, ...
    # EN: Letter style: 1=A, 2=B, ..., 26=Z, 27=AA, 28=AB, ...
    rest, buchstaben = max(1, zahl), ""
    while rest > 0:
        rest, remainder = divmod(rest - 1, 26)
        buchstaben = chr(ord("A") + remainder) + buchstaben
    return buchstaben if stil == "A" else buchstaben.lower()


@dataclass
class Beschriftungsgruppe:
    """DE: Eine berechnete Beschriftungsgruppe fuer die Anzeige in der
        Uebersicht -- start_index/end_index sind 0-basierte Positionen in
        der aktuellen Seitenliste (nicht im spaeteren PDF-Export, falls
        Teilungen die Seitenzahl noch veraendern).
    EN: A computed label group for display in the overview --
        start_index/end_index are 0-based positions in the current page
        list (not the later PDF export, if splits still change the page
        count)."""

    start_index: int
    end_index: int  # DE: einschliesslich / EN: inclusive
    stil: str
    praefix: str
    start: int

    @property
    def anzahl(self) -> int:
        return self.end_index - self.start_index + 1

    @property
    def erste_beschriftung(self) -> str:
        return self.praefix + (_formatiert(self.stil, self.start) if self.stil else "")

    @property
    def letzte_beschriftung(self) -> str:
        if not self.stil:
            return self.praefix
        return self.praefix + _formatiert(self.stil, self.start + self.anzahl - 1)

    @property
    def naechste_nummer(self) -> int:
        """DE: Nummer, mit der eine Fortsetzung dieser Gruppe (z. B. auf
            weiter hinten liegenden, markierten Seiten) beginnen sollte.
        EN: Number a continuation of this group (e.g. on further-back,
            marked pages) should start at."""
        return self.start + self.anzahl


def gruppen_berechnen(seiten: list[WorkingPage]) -> list[Beschriftungsgruppe]:
    """
    DE: Liefert alle definierten Beschriftungsgruppen in Seitenreihenfolge,
        mit berechnetem Endindex je Gruppe (bis zur naechsten Gruppe bzw.
        Listenende).
    EN: Returns all defined label groups in page order, with a computed
        end index per group (up to the next group resp. end of list).
    """
    marker = [i for i, wp in enumerate(seiten) if wp.beschriftung_stil is not None]
    gruppen = []
    for pos, start_index in enumerate(marker):
        end_index = (marker[pos + 1] - 1) if pos + 1 < len(marker) else len(seiten) - 1
        wp = seiten[start_index]
        gruppen.append(Beschriftungsgruppe(
            start_index=start_index, end_index=end_index,
            stil=wp.beschriftung_stil, praefix=wp.beschriftung_praefix, start=wp.beschriftung_start,
        ))
    return gruppen
