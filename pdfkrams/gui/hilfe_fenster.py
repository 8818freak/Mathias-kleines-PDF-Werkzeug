"""
DE: Eigenstaendiges Hilfe-Fenster -- zeigt die gebuendelte Bedienungs-
    anleitung (dieselbe HTML-Datei wie die druckbare Anleitung, siehe
    pdfkrams/hilfe/) in einem simplen, schnellen QTextBrowser statt in
    einem externen PDF-Betrachter oder Browser. Funktioniert identisch
    auf macOS UND Windows, ohne zusaetzliche Abhaengigkeit (kein
    QtWebEngine). Auf macOS ergaenzt dies das native, per Cmd+? bzw. ueber
    das Hilfe-Menue erreichbare Apple-Help-Book (siehe build_mac.sh) --
    dieses Fenster ist dort die garantiert funktionierende Rueckfalloption,
    falls die Systemintegration aus irgendeinem Grund nicht greift.

    QTextBrowser rendert nur eine Teilmenge von HTML/CSS (kein CSS-Grid,
    kein "position: sticky", kein Flexbox) -- die feine Zwei-Spalten-
    Optik der Datei geht dabei verloren, Text/Bilder/Ueberschriften/Listen/
    interne Sprungmarken (#anker-Links) bleiben aber vollstaendig
    erhalten und nutzbar.

EN: Standalone help window -- displays the bundled user manual (the same
    HTML file as the printable manual, see pdfkrams/hilfe/) in a simple,
    fast QTextBrowser instead of an external PDF viewer or browser. Works
    identically on macOS AND Windows, with no extra dependency (no
    QtWebEngine). On macOS this complements the native Apple Help Book
    reachable via Cmd+? resp. the Help menu (see build_mac.sh) -- this
    window is the guaranteed-working fallback there, in case the system
    integration doesn't engage for whatever reason.

    QTextBrowser only renders a subset of HTML/CSS (no CSS grid, no
    "position: sticky", no flexbox) -- the file's fine two-column look is
    lost, but text/images/headings/lists/internal anchor links stay
    fully intact and usable.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QKeySequence, QShortcut, QTextDocument
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTextBrowser, QVBoxLayout, QWidget

_HILFE_ORDNER = Path(__file__).parent.parent / "hilfe"


def hilfe_datei(sprachcode: str) -> Path:
    """DE: Pfad zur gebuendelten Hilfe-HTML-Datei fuer `sprachcode`
        ("de"/"en") -- faellt auf Deutsch zurueck, falls die Sprache
        unbekannt ist.
    EN: Path to the bundled help HTML file for `sprachcode` ("de"/"en")
        -- falls back to German if the language is unknown."""
    ordner = _HILFE_ORDNER / (sprachcode if sprachcode in ("de", "en") else "de")
    return ordner / "anleitung.html"


class HilfeFenster(QWidget):
    """DE: Fenster mit der Bedienungsanleitung als durchsuchbarer/scrollbarer Text.
    EN: Window with the user manual as searchable/scrollable text."""

    def __init__(self, sprachcode: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Bedienungsanleitung"))
        self.resize(900, 800)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        # DE: Suchpfad auf den Sprachordner setzen, damit relative
        #     Bildpfade (z. B. "bilder/0_pdf_erstellen.jpg") gefunden
        #     werden, ohne die HTML-Datei selbst anfassen zu muessen.
        # EN: Set the search path to the language folder, so relative
        #     image paths (e.g. "bilder/0_pdf_erstellen.jpg") are found
        #     without having to touch the HTML file itself.
        datei = hilfe_datei(sprachcode)
        self._browser.setSearchPaths([str(datei.parent)])
        self._browser.setSource(QUrl.fromLocalFile(str(datei)))

        # DE: Einfache Textsuche -- Cmd/Strg+F fokussiert das Suchfeld,
        #     Eingabetaste springt zum naechsten Treffer (mit Umschalt
        #     rueckwaerts), Treffer werden hervorgehoben.
        # EN: Simple text search -- Cmd/Ctrl+F focuses the search field,
        #     Enter jumps to the next match (Shift for backwards),
        #     matches are highlighted.
        such_zeile = QHBoxLayout()
        such_zeile.addWidget(QLabel(self.tr("Suchen:")))
        self._suchfeld = QLineEdit()
        self._suchfeld.setPlaceholderText(self.tr("Text in der Anleitung suchen …"))
        self._suchfeld.returnPressed.connect(lambda: self._suchen(rueckwaerts=False))
        such_zeile.addWidget(self._suchfeld)

        QShortcut(QKeySequence.StandardKey.Find, self, activated=self._suchfeld.setFocus)
        QShortcut(QKeySequence.StandardKey.FindNext, self, activated=lambda: self._suchen(rueckwaerts=False))
        QShortcut(QKeySequence.StandardKey.FindPrevious, self, activated=lambda: self._suchen(rueckwaerts=True))

        layout = QVBoxLayout(self)
        layout.addLayout(such_zeile)
        layout.addWidget(self._browser)

    def _suchen(self, rueckwaerts: bool) -> None:
        text = self._suchfeld.text()
        if not text:
            return
        flags = QTextDocument.FindFlag.FindBackward if rueckwaerts else QTextDocument.FindFlag(0)
        if not self._browser.find(text, flags):
            # DE: Kein Treffer ab der aktuellen Position -- von vorne
            #     (bzw. hinten) beginnen, statt einfach nichts zu tun.
            # EN: No match from the current position -- start over from
            #     the beginning (resp. end) instead of just doing nothing.
            cursor = self._browser.textCursor()
            cursor.movePosition(
                cursor.MoveOperation.End if rueckwaerts else cursor.MoveOperation.Start
            )
            self._browser.setTextCursor(cursor)
            self._browser.find(text, flags)
