"""
DE: Hauptfenster der Anwendung. Drei Spalten: links die Werkzeug-Auswahl,
    in der Mitte die gemeinsame Dateiliste (gilt fuer alle Werkzeuge --
    einmal laden, mit mehreren Werkzeugen nacheinander bearbeiten), rechts
    die Steuerung des jeweils aktiven Werkzeugs. Neue Werkzeuge werden ueber
    _WERKZEUGE registriert -- fertige bekommen eine echte Klasse, kuenftige
    vorerst None (werden dann als "bald verfuegbar" angezeigt).

    Dazu ein normales Menü (Datei/Bearbeiten) mit den ueblichen
    Systembefehlen -- Oeffnen, Speichern, Speichern unter, Rueckgaengig,
    Wiederholen -- inklusive der ueblichen Tastenkuerzel (Cmd+O, Cmd+S,
    Cmd+Z, …), die unter macOS automatisch im nativen Menu greifen.

EN: Main application window. Three columns: tool selection on the left, the
    shared file list in the middle (applies to every tool -- load once,
    work through several tools one after another), the active tool's
    controls on the right. New tools are registered via _WERKZEUGE --
    finished ones get a real class, upcoming ones get None for now (shown
    as "coming soon").

    Plus a normal menu (File/Edit) with the usual system commands -- Open,
    Save, Save As, Undo, Redo -- including the usual keyboard shortcuts
    (Cmd+O, Cmd+S, Cmd+Z, …), which automatically work via the native menu
    on macOS.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QWidget,
)

from pdfkrams.core.combine import export_pdf
from pdfkrams.core.document import datei_aufschluesseln
from pdfkrams.core.update_check import neueste_version_pruefen
from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.einstellungen_dialog import EinstellungenDialog
from pdfkrams.gui.hilfe_fenster import HilfeFenster
from pdfkrams.gui.tools.bildbereinigung_tool import BildbereinigungToolWidget
from pdfkrams.gui.tools.combine_tool import CombineToolWidget
from pdfkrams.gui.tools.heftseiten_tool import HeftseitenToolWidget
from pdfkrams.gui.tools.leerseiten_tool import LeerseitenToolWidget
from pdfkrams.gui.tools.lesezeichen_tool import LesezeichenToolWidget
from pdfkrams.gui.tools.metadaten_tool import MetadatenToolWidget
from pdfkrams.gui.tools.nummerieren_tool import NummerierenToolWidget
from pdfkrams.gui.tools.passwortschutz_tool import PasswortschutzToolWidget
from pdfkrams.gui.tools.pdf_zu_bildern_tool import PdfZuBildernToolWidget
from pdfkrams.gui.tools.reparatur_tool import ReparaturToolWidget
from pdfkrams.gui.tools.rotate_tool import RotateToolWidget
from pdfkrams.gui.tools.schwaerzung_tool import SchwaerzungToolWidget
from pdfkrams.gui.tools.seitenbeschriftung_tool import SeitenbeschriftungToolWidget
from pdfkrams.gui.tools.seitenmass_tool import SeitenmassToolWidget
from pdfkrams.gui.tools.split_tool import SplitToolWidget
from pdfkrams.gui.tools.verkleinern_tool import VerkleinernToolWidget
from pdfkrams.gui.tools.zuschneiden_tool import ZuschneidenToolWidget
from pdfkrams.gui.tools.zusammenfuegen_tool import ZusammenfuegenToolWidget
from pdfkrams.gui.widgets.datei_dialoge import speichern_dialog
from pdfkrams.gui.widgets.file_tool_base import DateiListenPanel
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.hintergrund import im_hintergrund_ausfuehren, im_hintergrund_still_ausfuehren
from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.info import ANBIETER, VERSION, WEBSITE, copyright_zeile, voller_programmname

# DE: Logo des Anbieters (Telefonanleitungen.de) -- im Ueber-Dialog
#     gezeigt, damit direkt erkennbar ist, wer dieses Programm
#     bereitstellt. Gebuendelter Pfad, siehe build_mac.sh/
#     build_windows.bat (--add-data fuer pdfkrams/logo).
# EN: Provider's logo (Telefonanleitungen.de) -- shown in the About
#     dialog, so it's immediately visible who provides this program.
#     Bundled path, see build_mac.sh/build_windows.bat (--add-data for
#     pdfkrams/logo).
_LOGO_PFAD = Path(__file__).parent.parent / "logo" / "telefonanleitungen.png"

# DE: Reihenfolge und Beschriftung der Werkzeuge in der Seitenleiste.
#     None = noch nicht implementiert, wird als Platzhalter angezeigt.
#     Jede Klasse muss (liste: PageListWidget, parent=None) entgegennehmen.
# EN: Order and label of tools in the sidebar.
#     None = not implemented yet, shown as a placeholder.
#     Every class must accept (liste: PageListWidget, parent=None).
_WERKZEUGE: list[tuple[str, type[QWidget] | None]] = [
    ("PDF erstellen", CombineToolWidget),
    ("Seiten drehen", RotateToolWidget),
    ("Bildbereinigung", BildbereinigungToolWidget),
    ("Leerseiten entfernen", LeerseitenToolWidget),
    ("Seiten teilen", SplitToolWidget),
    ("Seiten zusammenfügen", ZusammenfuegenToolWidget),
    ("Heftseiten teilen", HeftseitenToolWidget),
    ("Seiten nummerieren", NummerierenToolWidget),
    ("Lesezeichen setzen", LesezeichenToolWidget),
    ("Seiten benennen", SeitenbeschriftungToolWidget),
    ("Seitenmaß normieren", SeitenmassToolWidget),
    ("Seiten zuschneiden", ZuschneidenToolWidget),
    ("Schwärzen", SchwaerzungToolWidget),
    ("PDF in Bilder teilen", PdfZuBildernToolWidget),
    ("PDF verkleinern & PDF/A", VerkleinernToolWidget),
    ("PDF reparieren & entsperren", ReparaturToolWidget),
    ("Passwortschutz", PasswortschutzToolWidget),
    ("Metadaten bearbeiten", MetadatenToolWidget),
]


class _WerkzeugStack(QStackedWidget):
    """
    DE: QStackedWidget berechnet seine Mindestgroesse standardmaessig aus
        dem GROESSTEN aller enthaltenen Werkzeuge -- auch der gerade
        unsichtbaren. Ein einziges besonders breites Werkzeug (z. B. eine
        Zeile mit mehreren Kontrollkaestchen ohne Zeilenumbruch) blockiert
        dadurch den Splitter zwischen Dateiliste und Werkzeugbereich fuer
        ALLE Werkzeuge, nicht nur fuer sich selbst -- genau das hat der
        Nutzer als "Verschieben der Spaltenbreite geht nicht" gemeldet.
        Diese Unterklasse berichtet stattdessen nur die Groesse des
        AKTUELL sichtbaren Werkzeugs.
    EN: QStackedWidget computes its minimum size from the LARGEST of all
        contained tools by default -- even ones currently invisible. One
        single especially wide tool (e.g. a row of several checkboxes
        with no line wrap) therefore blocks the splitter between the
        file list and the tool area for ALL tools, not just itself --
        exactly what the user reported as "moving the column width
        doesn't work". This subclass instead reports only the size of
        the CURRENTLY visible tool.
    """

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt-Namenskonvention)
        aktuell = self.currentWidget()
        return aktuell.sizeHint() if aktuell is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt-Namenskonvention)
        aktuell = self.currentWidget()
        return aktuell.minimumSizeHint() if aktuell is not None else super().minimumSizeHint()


def _platzhalter(name: str) -> QWidget:
    """DE: Hinweisseite fuer ein noch nicht gebautes Werkzeug.
    EN: Placeholder page for a tool that hasn't been built yet."""
    text = QCoreApplication.translate("MainWindow", "„{0}“ kommt in einem der nächsten Schritte.").format(name)
    label = QLabel(text)
    label.setStyleSheet("color: gray; padding: 24px;")
    return label


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(voller_programmname())
        self.resize(1300, 750)

        self._letzter_pdf_pfad: Path | None = None
        self._hilfe_fenster: HilfeFenster | None = None
        # DE: Ob es seit dem letzten erfolgreichen Speichern (bzw. seit dem
        #     Start/letzten "Datei schliessen") Aenderungen an der Liste
        #     gab -- fuer die Rueckfrage bei "Datei schliessen" und beim
        #     Beenden der App (siehe _als_ungespeichert_markieren,
        #     _datei_schliessen, closeEvent).
        # EN: Whether there have been changes to the list since the last
        #     successful save (resp. since startup/the last "Close file")
        #     -- for the confirmation prompt on "Close file" and on
        #     quitting the app (see _als_ungespeichert_markieren,
        #     _datei_schliessen, closeEvent).
        self._ungespeicherte_aenderungen = False

        self._dateiliste_panel = DateiListenPanel()
        self._liste: PageListWidget = self._dateiliste_panel.liste
        self._dateiliste_panel.einzelneDateiGeoeffnet.connect(self._dokument_geoeffnet)
        self._dateiliste_panel.andereDateienHinzugefuegt.connect(self._speicherziel_verwerfen)
        self._liste.geaendert.connect(self._als_ungespeichert_markieren)
        self._liste.alsExportiertMarkiert.connect(self._exportziel_uebernehmen)

        self._seitenleiste = QListWidget()
        self._werkzeuge = _WerkzeugStack()

        for name, widget_klasse in _WERKZEUGE:
            # DE: self.tr(name) statt eines literalen Strings -- pyside6-lupdate
            #     kann das nicht automatisch extrahieren, da `name` eine
            #     Variable ist; die Uebersetzungen fuer diese neun Namen
            #     werden von Hand in der .ts-Datei ergaenzt (siehe
            #     uebersetzungen/README bzw. Kommentar dort).
            # EN: self.tr(name) instead of a literal string -- pyside6-lupdate
            #     can't auto-extract this since `name` is a variable; the
            #     translations for these nine names are added by hand to
            #     the .ts file (see uebersetzungen/README resp. the
            #     comment there).
            self._seitenleiste.addItem(self.tr(name))
            self._werkzeuge.addWidget(widget_klasse(self._liste) if widget_klasse else _platzhalter(name))

        self._seitenleiste.currentRowChanged.connect(self._werkzeuge.setCurrentIndex)
        # DE: Qt merkt von selbst nicht, dass sich minimumSizeHint() durch
        #     den Wechsel des sichtbaren Werkzeugs geaendert hat (siehe
        #     _WerkzeugStack) -- updateGeometry() stoesst die Neuberechnung
        #     im Splitter darueber an.
        # EN: Qt doesn't notice on its own that minimumSizeHint() changed
        #     because the visible tool changed (see _WerkzeugStack) --
        #     updateGeometry() triggers the splitter's recalculation above it.
        self._werkzeuge.currentChanged.connect(lambda _i: self._werkzeuge.updateGeometry())
        self._seitenleiste.setCurrentRow(0)
        self._seitenleiste.setFixedWidth(180)

        splitter = QSplitter()
        splitter.addWidget(self._seitenleiste)
        splitter.addWidget(self._dateiliste_panel)
        splitter.addWidget(self._werkzeuge)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        # DE: Breitere Griffflaeche -- der Standard (1 px) ist auf macOS
        #     kaum zu treffen, was den Eindruck erweckt, die mittlere
        #     Spalte (Dateiliste) liesse sich gar nicht in der Breite
        #     anpassen. setChildrenCollapsible(False) verhindert zudem,
        #     dass ein zu weiter Zug eine Spalte versehentlich auf 0 px
        #     zusammenschiebt.
        # EN: Wider grab area -- the default (1 px) is hard to hit on
        #     macOS, which gives the impression that the middle column
        #     (file list) can't be resized at all. setChildrenCollapsible
        #     (False) also prevents an over-eager drag from accidentally
        #     collapsing a column to 0 px.
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)
        gemerkte_groessen = einstellungen.splitter_groessen()
        if gemerkte_groessen and len(gemerkte_groessen) == 3:
            splitter.setSizes(gemerkte_groessen)
        splitter.splitterMoved.connect(lambda *_: einstellungen.splitter_groessen_setzen(splitter.sizes()))

        self._splitter = splitter
        self._seitenleiste.setVisible(einstellungen.werkzeugliste_sichtbar())

        self.setCentralWidget(splitter)
        self._menu_erstellen()

    # -- Menü / menu ------------------------------------------------------

    def _menu_erstellen(self) -> None:
        menu = self.menuBar()

        datei_menu = menu.addMenu(self.tr("Datei"))

        action_oeffnen = QAction(self.tr("Dateien öffnen …"), self)
        action_oeffnen.setShortcut(QKeySequence.StandardKey.Open)
        action_oeffnen.triggered.connect(self._dateiliste_panel.dateien_hinzufuegen_dialog)
        datei_menu.addAction(action_oeffnen)

        self._action_schliessen = QAction(self.tr("Datei schließen"), self)
        self._action_schliessen.setShortcut(QKeySequence.StandardKey.Close)
        self._action_schliessen.triggered.connect(self._datei_schliessen)
        self._action_schliessen.setEnabled(False)
        self._liste.geaendert.connect(
            lambda: self._action_schliessen.setEnabled(self._liste.count() > 0)
        )
        datei_menu.addAction(self._action_schliessen)

        datei_menu.addSeparator()

        self._action_speichern = QAction(self.tr("Speichern"), self)
        self._action_speichern.setShortcut(QKeySequence.StandardKey.Save)
        self._action_speichern.triggered.connect(self._speichern)
        datei_menu.addAction(self._action_speichern)

        action_speichern_unter = QAction(self.tr("Speichern unter …"), self)
        action_speichern_unter.setShortcut(QKeySequence.StandardKey.SaveAs)
        action_speichern_unter.triggered.connect(self._speichern_unter)
        datei_menu.addAction(action_speichern_unter)

        bearbeiten_menu = menu.addMenu(self.tr("Bearbeiten"))

        self._action_rueckgaengig = QAction(self.tr("Rückgängig"), self)
        self._action_rueckgaengig.setShortcut(QKeySequence.StandardKey.Undo)
        self._action_rueckgaengig.triggered.connect(self._liste.rueckgaengig)
        bearbeiten_menu.addAction(self._action_rueckgaengig)

        self._action_wiederholen = QAction(self.tr("Wiederholen"), self)
        self._action_wiederholen.setShortcut(QKeySequence.StandardKey.Redo)
        self._action_wiederholen.triggered.connect(self._liste.wiederholen)
        bearbeiten_menu.addAction(self._action_wiederholen)

        self._liste.verlaufGeaendert.connect(self._verlauf_aktualisieren)
        self._verlauf_aktualisieren()

        bearbeiten_menu.addSeparator()

        # DE: Ausschneiden/Kopieren/Einfuegen/Alles auswaehlen -- auf macOS
        #     NOETIG, damit Cmd+X/C/V/A ueberhaupt funktionieren: ohne ein
        #     Menue mit diesen Standard-Tastenkuerzeln registriert AppKit
        #     sie nirgends, wodurch Cmd+V (u. a.) selbst in normalen
        #     Textfeldern -- etwa dem Dateinamen-Feld im Speichern-Dialog
        #     -- ins Leere lief; ueber das Rechtsklick-Kontextmenue ging
        #     Einfuegen dagegen immer, da das direkt am Pasteboard
        #     vorbeigeht, nicht ueber die Menuleiste. QApplication.
        #     focusWidget() traegt die eigentliche Aktion, falls das
        #     fokussierte Feld sie unterstuetzt (QLineEdit/QTextEdit fuer
        #     Ausschneiden/Kopieren/Einfuegen; zusaetzlich QAbstractItemView
        #     -- also auch die gemeinsame Seitenliste selbst -- fuer Alles
        #     auswaehlen: Cmd+A dort sollte natuerlich alle Seiten
        #     markieren, nicht wirkungslos bleiben).
        # EN: Cut/Copy/Paste/Select All -- NECESSARY on macOS for
        #     Cmd+X/C/V/A to work at all: without a menu registering these
        #     standard shortcuts, AppKit doesn't route them anywhere,
        #     which meant Cmd+V (among others) did nothing even in plain
        #     text fields -- e.g. the filename field in the Save dialog --
        #     while right-click paste always worked there, since that
        #     goes straight through the pasteboard rather than the menu
        #     bar. QApplication.focusWidget() carries out the actual
        #     action, if the focused field supports it (QLineEdit/
        #     QTextEdit for Cut/Copy/Paste; also QAbstractItemView -- i.e.
        #     the shared page list itself -- for Select All: Cmd+A there
        #     should naturally select all pages, not do nothing).
        def _fokus_aktion(methode: str) -> None:
            feld = QApplication.focusWidget()
            if isinstance(feld, (QLineEdit, QTextEdit, QAbstractItemView)) and hasattr(feld, methode):
                getattr(feld, methode)()

        action_ausschneiden = QAction(self.tr("Ausschneiden"), self)
        action_ausschneiden.setShortcut(QKeySequence.StandardKey.Cut)
        action_ausschneiden.triggered.connect(lambda: _fokus_aktion("cut"))
        bearbeiten_menu.addAction(action_ausschneiden)

        action_kopieren = QAction(self.tr("Kopieren"), self)
        action_kopieren.setShortcut(QKeySequence.StandardKey.Copy)
        action_kopieren.triggered.connect(lambda: _fokus_aktion("copy"))
        bearbeiten_menu.addAction(action_kopieren)

        action_einfuegen = QAction(self.tr("Einfügen"), self)
        action_einfuegen.setShortcut(QKeySequence.StandardKey.Paste)
        action_einfuegen.triggered.connect(lambda: _fokus_aktion("paste"))
        bearbeiten_menu.addAction(action_einfuegen)

        action_alles_auswaehlen = QAction(self.tr("Alles auswählen"), self)
        action_alles_auswaehlen.setShortcut(QKeySequence.StandardKey.SelectAll)
        action_alles_auswaehlen.triggered.connect(lambda: _fokus_aktion("selectAll"))
        bearbeiten_menu.addAction(action_alles_auswaehlen)

        bearbeiten_menu.addSeparator()

        # DE: Kehrt die Reihenfolge der Seiten um -- bei markiertem Block
        #     nur dessen Reihenfolge, sonst die ganze Liste (siehe
        #     PageListWidget.reihenfolge_umkehren() fuer die genaue
        #     Semantik). Wirkt auf die gemeinsame Seitenliste, ist also
        #     unabhaengig vom gerade offenen Werkzeug immer verfuegbar.
        # EN: Reverses the page order -- just the selected block if one
        #     is marked, otherwise the whole list (see PageListWidget.
        #     reihenfolge_umkehren() for the exact semantics). Acts on the
        #     shared page list, so it's always available regardless of
        #     which tool is currently open.
        action_reihenfolge_umkehren = QAction(self.tr("Reihenfolge umkehren"), self)
        action_reihenfolge_umkehren.triggered.connect(self._liste.reihenfolge_umkehren)
        bearbeiten_menu.addAction(action_reihenfolge_umkehren)

        bearbeiten_menu.addSeparator()

        action_einstellungen = QAction(self.tr("Einstellungen …"), self)
        action_einstellungen.setShortcut(QKeySequence.StandardKey.Preferences)
        # DE: PreferencesRole -- macOS verschiebt diesen Eintrag automatisch
        #     in das native Anwendungsmenü (Cmd+,).
        # EN: PreferencesRole -- macOS automatically moves this entry into
        #     the native application menu (Cmd+,).
        action_einstellungen.setMenuRole(QAction.MenuRole.PreferencesRole)
        action_einstellungen.triggered.connect(self._einstellungen_anzeigen)
        bearbeiten_menu.addAction(action_einstellungen)

        ansicht_menu = menu.addMenu(self.tr("Ansicht"))

        self._action_werkzeugliste = QAction(self.tr("Werkzeugliste einblenden"), self)
        self._action_werkzeugliste.setCheckable(True)
        # DE: NICHT self._seitenleiste.isVisible() -- das Fenster wurde an
        #     dieser Stelle noch nicht angezeigt (show() passiert erst
        #     spaeter von aussen), weshalb isVisible() hier IMMER False
        #     liefert, ganz unabhaengig vom tatsaechlich per setVisible()
        #     gesetzten Zustand. Direkt aus der Einstellung lesen.
        # EN: NOT self._seitenleiste.isVisible() -- the window hasn't been
        #     shown yet at this point (show() only happens later from the
        #     outside), so isVisible() ALWAYS returns False here,
        #     regardless of the state actually set via setVisible(). Read
        #     directly from the setting instead.
        self._action_werkzeugliste.setChecked(einstellungen.werkzeugliste_sichtbar())
        # DE: NICHT F4 (macOS faengt das systemweit fuer Spotlight ab,
        #     bevor es die App je erreicht) und NICHT Cmd+\ (Symbol-
        #     Tasten wie "\" liegen auf nicht-US-Tastaturlayouts an ganz
        #     anderen physischen Positionen bzw. brauchen andere
        #     Zusatztasten, wodurch QKeySequence("Ctrl+\\") dort ins
        #     Leere lief -- beides nutzerseitig bestaetigt). Eine reine
        #     Buchstaben-Kombination ist ueber alle Tastaturlayouts hinweg
        #     zuverlaessig.
        # EN: NOT F4 (macOS intercepts that system-wide for Spotlight
        #     before it ever reaches the app) and NOT Cmd+\ (symbol keys
        #     like "\" sit at entirely different physical positions on
        #     non-US keyboard layouts resp. need different modifier keys,
        #     which made QKeySequence("Ctrl+\\") a no-op there -- both
        #     confirmed by the user). A plain letter combination is
        #     reliable across every keyboard layout.
        self._action_werkzeugliste.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self._action_werkzeugliste.toggled.connect(self._werkzeugliste_umschalten)
        ansicht_menu.addAction(self._action_werkzeugliste)

        werkzeuge_menu = menu.addMenu(self.tr("Werkzeuge"))
        werkzeuge_gruppe = QActionGroup(self)
        werkzeuge_gruppe.setExclusive(True)
        for i, (name, _widget_klasse) in enumerate(_WERKZEUGE):
            # DE: self.tr(name) -- dieselben Zeichenketten wie in der
            #     Seitenleiste oben, daher bereits uebersetzt vorhanden
            #     (siehe der Kommentar dort), keine neuen .ts-Eintraege
            #     noetig.
            # EN: self.tr(name) -- the same strings as in the sidebar
            #     above, so already translated (see the comment there),
            #     no new .ts entries needed.
            action = QAction(self.tr(name), self)
            action.setCheckable(True)
            action.setChecked(i == self._seitenleiste.currentRow())
            action.triggered.connect(lambda _checked=False, i=i: self._seitenleiste.setCurrentRow(i))
            werkzeuge_gruppe.addAction(action)
            werkzeuge_menu.addAction(action)
        self._seitenleiste.currentRowChanged.connect(
            lambda zeile: werkzeuge_gruppe.actions()[zeile].setChecked(True)
        )

        hilfe_menu = menu.addMenu(self.tr("Hilfe"))

        action_anleitung = QAction(self.tr("Bedienungsanleitung"), self)
        # DE: StandardKey.HelpContents -- auf macOS automatisch Cmd+?,
        #     unter Windows automatisch F1 (Qt kennt die jeweils
        #     uebliche Systemtaste fuer "Hilfe anzeigen").
        # EN: StandardKey.HelpContents -- automatically Cmd+? on macOS,
        #     F1 on Windows (Qt knows each platform's conventional
        #     "show help" key).
        action_anleitung.setShortcut(QKeySequence.StandardKey.HelpContents)
        action_anleitung.triggered.connect(self._anleitung_anzeigen)
        hilfe_menu.addAction(action_anleitung)
        hilfe_menu.addSeparator()

        action_ueber = QAction(self.tr("Über {0} …").format(voller_programmname()), self)
        # DE: AboutRole -- macOS verschiebt diesen Eintrag automatisch in
        #     das native Anwendungsmenü ("Über Mathias' kleines ...").
        # EN: AboutRole -- macOS automatically moves this entry into the
        #     native application menu ("About Mathias' kleines ...").
        action_ueber.setMenuRole(QAction.MenuRole.AboutRole)
        action_ueber.triggered.connect(self._ueber_anzeigen)
        hilfe_menu.addAction(action_ueber)

        action_update_suchen = QAction(self.tr("Nach Updates suchen …"), self)
        # DE: ApplicationSpecificRole -- macOS ordnet diesen Eintrag
        #     ebenfalls im nativen Anwendungsmenü ein, direkt neben
        #     "Über ..." (macOS-uebliche Stelle fuer manuelle Update-
        #     Pruefungen, z. B. bei allen Sparkle-basierten Apps).
        # EN: ApplicationSpecificRole -- macOS also places this entry in
        #     the native application menu, right next to "About ..."
        #     (the macOS-conventional spot for manual update checks,
        #     e.g. in all Sparkle-based apps).
        action_update_suchen.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)
        action_update_suchen.triggered.connect(self._update_manuell_pruefen)
        hilfe_menu.addAction(action_update_suchen)

    def _update_manuell_pruefen(self) -> None:
        """DE: Manuelle, vom Nutzer angestossene Update-Pruefung (Menue
            "Nach Updates suchen …") -- anders als
            update_pruefen_falls_aktiviert() UNABHAENGIG von der
            Einstellung "Beim Start nach neuen Versionen suchen" (die
            betrifft nur die stille Pruefung beim Programmstart) und MIT
            sichtbarer Fortschrittsanzeige sowie einer Rueckmeldung auch
            dann, wenn keine neuere Version gefunden wurde.
        EN: Manual, user-initiated update check (menu "Check for
            updates …") -- unlike update_pruefen_falls_aktiviert(),
            INDEPENDENT of the "Check for new versions on startup" setting
            (which only concerns the silent check on program start) and
            WITH a visible progress indicator plus feedback even when no
            newer version was found."""
        try:
            info = im_hintergrund_ausfuehren(self, self.tr("Suche nach Updates …"), neueste_version_pruefen)
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.warning(self, self.tr("Prüfung fehlgeschlagen"), str(exc))
            return
        if info is None:
            QMessageBox.information(
                self, self.tr("Kein Update verfügbar"),
                self.tr("Keine neuere Version gefunden (aktuelle Version: {0}). Falls keine "
                       "Internetverbindung besteht, lässt sich das nicht von „bereits aktuell“ "
                       "unterscheiden.").format(VERSION),
            )
            return
        self._update_gefunden(info)

    def _ueber_anzeigen(self) -> None:
        # DE: Eigene QMessageBox statt der .about()-Kurzform -- die
        #     Kurzform stellt unter macOS den GESAMTEN Text fett dar (dort
        #     gilt alles als "Haupttext"). Mit text()/informativeText()
        #     bleibt nur der Programmname fett, der Rest normal, wie bei
        #     einem nativen macOS-Info-Fenster ueblich.
        # EN: A plain QMessageBox instead of the .about() convenience
        #     function -- on macOS that renders the ENTIRE text in bold
        #     (everything counts as "main text" there). Using
        #     text()/informativeText() keeps only the program name bold and
        #     the rest normal, matching a native macOS info window.
        box = QMessageBox(self)
        box.setWindowTitle(self.tr("Über {0}").format(voller_programmname()))
        logo = QPixmap(str(_LOGO_PFAD))
        if not logo.isNull():
            box.setIconPixmap(logo.scaledToWidth(280, Qt.TransformationMode.SmoothTransformation))
        box.setText(voller_programmname())
        box.setInformativeText(
            self.tr("Kostenlos bereitgestellt von {0}<br>"
                   "<a href=\"{1}\">{1}</a><br><br>"
                   "{2}<br>"
                   "Dieses Programm kommt OHNE JEDE GEWÄHRLEISTUNG. Es ist freie "
                   "Software, und Sie dürfen es unter bestimmten Bedingungen "
                   "weiterverbreiten -- siehe die Lizenz GNU GPL 3.0 (Datei "
                   "LICENSE) für Details.<br><br>"
                   "Entwickelt und getestet wird ausschließlich auf macOS -- die "
                   "Windows-Version wird nicht selbst getestet, funktioniert aber "
                   "hoffentlich fehlerfrei. Bei Fehlern bitte mit einer genauen, "
                   "nachvollziehbaren Beschreibung an "
                   "<a href=\"mailto:telefonmann@telefonanleitungen.de\">"
                   "telefonmann@telefonanleitungen.de</a> schreiben, dann wird so "
                   "schnell wie möglich korrigiert."
                   ).format(ANBIETER, WEBSITE, copyright_zeile())
        )
        box.exec()

    def _einstellungen_anzeigen(self) -> None:
        EinstellungenDialog(self).exec()

    def _anleitung_anzeigen(self) -> None:
        # DE: Dasselbe Fenster wiederverwenden statt bei jedem Aufruf ein
        #     neues zu erzeugen -- sonst haeufen sich bei mehrfachem
        #     Cmd+?/F1 unnoetig viele Fenster an. Referenz auf self
        #     noetig, sonst raeumt Python das Fenster sofort wieder weg.
        # EN: Reuse the same window instead of creating a new one on
        #     every call -- otherwise pressing Cmd+?/F1 repeatedly piles
        #     up needless windows. Reference on self needed, otherwise
        #     Python garbage-collects the window immediately.
        if self._hilfe_fenster is None:
            self._hilfe_fenster = HilfeFenster(einstellungen.sprache())
        self._hilfe_fenster.show()
        self._hilfe_fenster.raise_()
        self._hilfe_fenster.activateWindow()

    # -- Update-Pruefung / update check --------------------------------------

    def update_pruefen_falls_aktiviert(self) -> None:
        """DE: Prueft still im Hintergrund auf eine neuere Version, aber
            NUR wenn der Nutzer das in den Einstellungen ausdruecklich
            eingeschaltet hat (Standard: aus, siehe einstellungen.py's
            updates_pruefen() -- dann stellt die App ueberhaupt keine
            Internetverbindung her). Ohne sichtbaren Fortschrittsdialog
            (im_hintergrund_still_ausfuehren) -- ein Hinweisfenster
            erscheint nur, falls tatsaechlich eine neuere Version
            gefunden wurde, sonst bleibt der Vorgang unbemerkt.
        EN: Silently checks in the background for a newer version, but
            ONLY if the user has explicitly enabled it in Preferences
            (default: off, see einstellungen.py's updates_pruefen() --
            with it off, the app makes no internet connection at all).
            Without a visible progress dialog
            (im_hintergrund_still_ausfuehren) -- a notice only appears if
            a newer version was actually found, otherwise the check
            stays unnoticed."""
        if not einstellungen.updates_pruefen():
            return
        im_hintergrund_still_ausfuehren(self, neueste_version_pruefen, self._update_gefunden)

    def _update_gefunden(self, info) -> None:
        if info is None:
            return
        antwort = QMessageBox.information(
            self, self.tr("Update verfügbar"),
            self.tr("Version {0} ist verfügbar (installiert: {1}).\n\n"
                   "Jetzt die Release-Seite öffnen?").format(info.version, VERSION),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if antwort == QMessageBox.StandardButton.Yes and info.url:
            QDesktopServices.openUrl(QUrl(info.url))

    def dateien_oeffnen(self, pfade: list[Path]) -> None:
        """DE: Von aussen uebergebene Dateien in die Dateiliste laden --
            z. B. vom Finder ("Oeffnen mit …"), per Doppelklick oder ueber
            die Kommandozeile. Bringt das Fenster dabei in den Vordergrund,
            falls es (etwa beim erneuten Oeffnen einer Datei waehrend die
            App schon laeuft) im Hintergrund war.
        EN: Load externally supplied files into the file list -- e.g. from
            Finder's "Open With …", a double-click, or the command line.
            Also brings the window to the front, in case it was in the
            background (e.g. opening another file while the app is
            already running)."""
        self.show()
        self.raise_()
        self.activateWindow()
        self._dateiliste_panel._pfade_verarbeiten(pfade)

    def _verlauf_aktualisieren(self) -> None:
        self._action_rueckgaengig.setEnabled(self._liste.kann_rueckgaengig())
        self._action_wiederholen.setEnabled(self._liste.kann_wiederholen())

    def _werkzeugliste_umschalten(self, sichtbar: bool) -> None:
        """DE: Blendet die linke Werkzeugliste ein/aus (F4 bzw. Ansicht-
            Menue) -- mehr Platz fuer Dateiliste und Werkzeugbereich, wenn
            man sie nicht braucht. Merkt sich den Zustand fuer den
            naechsten Programmstart.
        EN: Shows/hides the left tool list (F4 resp. the View menu) --
            more room for the file list and tool area when it's not
            needed. Remembers the state for the next program launch."""
        self._seitenleiste.setVisible(sichtbar)
        einstellungen.werkzeugliste_sichtbar_setzen(sichtbar)

    # -- Speichern / saving -------------------------------------------------

    def _dokument_geoeffnet(self, pfad: Path) -> None:
        """DE: Merkt sich eine frisch geoeffnete Einzel-PDF als Speicherziel
            fuer "Speichern" (Cmd+S) -- so ueberschreibt Speichern direkt
            diese Datei, statt jedes Mal nach einem Ort zu fragen. Wird nur
            ausgeloest, wenn wirklich genau eine PDF in eine leere Liste
            geladen wurde (siehe DateiListenPanel.einzelneDateiGeoeffnet);
            sobald weitere Dateien hinzukommen, ist die Liste kein Abbild
            mehr dieser einen Datei, und "Speichern" fragt wieder nach.
        EN: Remembers a freshly opened single PDF as the save target for
            "Save" (Cmd+S) -- so Save overwrites that file directly
            instead of asking for a location every time. Only fires when
            exactly one PDF was loaded into an empty list (see
            DateiListenPanel.einzelneDateiGeoeffnet); once more files are
            added, the list no longer mirrors that one file, and "Save"
            asks again. Ausserdem gilt eine frisch, unveraendert geoeffnete
            Einzeldatei noch nicht als "ungespeichert" -- ihr Inhalt
            entspricht ja exakt dem, was schon auf der Platte liegt."""
        self._letzter_pdf_pfad = pfad
        self._ungespeicherte_aenderungen = False

    def _exportziel_uebernehmen(self, pfad: Path) -> None:
        """DE: Reagiert auf PageListWidget.alsExportiertMarkiert -- ein
            Werkzeug (z. B. "PDF erstellen", "Seiten drehen") hat die
            komplette aktuelle Seitenliste erfolgreich als PDF exportiert.
            Genau wie beim Oeffnen einer Einzeldatei gilt dieser Pfad
            danach als Speicherziel fuer "Speichern" (Cmd+S), und es gibt
            ab jetzt wieder keine ungespeicherten Aenderungen.
        EN: Reacts to PageListWidget.alsExportiertMarkiert -- a tool (e.g.
            "Create PDF", "Rotate pages") successfully exported the entire
            current page list as a PDF. Just like opening a single file,
            that path now counts as the save target for "Save" (Cmd+S),
            and there are once again no unsaved changes."""
        self._letzter_pdf_pfad = pfad
        self._ungespeicherte_aenderungen = False

    def _speicherziel_verwerfen(self) -> None:
        self._letzter_pdf_pfad = None
        # DE: Mehrere Dateien kombiniert (oder zu einer schon offenen Liste
        #     hinzugefuegt) -- das Ergebnis existiert so noch nirgends
        #     gespeichert auf der Platte.
        # EN: Several files combined (or added to an already-open list) --
        #     the result doesn't exist saved on disk anywhere like this yet.
        self._ungespeicherte_aenderungen = True

    def _als_ungespeichert_markieren(self) -> None:
        self._ungespeicherte_aenderungen = True

    def _ungespeicherte_aenderungen_bestaetigen(self, titel: str, frage: str) -> bool:
        """DE: Fragt nur nach, wenn es tatsaechlich ungespeicherte Aenderungen
            gibt; liefert True, wenn fortgefahren werden darf (keine
            Aenderungen, oder Nutzer hat trotzdem bestaetigt).
        EN: Only asks if there actually are unsaved changes; returns True
            if it's fine to proceed (no changes, or the user confirmed
            anyway)."""
        if not self._ungespeicherte_aenderungen or self._liste.count() == 0:
            return True
        antwort = QMessageBox.question(
            self, titel, frage,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return antwort == QMessageBox.StandardButton.Yes

    def _datei_schliessen(self) -> None:
        if not self._ungespeicherte_aenderungen_bestaetigen(
            self.tr("Ungespeicherte Änderungen"),
            self.tr("Diese Datei hat ungespeicherte Änderungen. Trotzdem schließen?"),
        ):
            return
        self._liste.dokument_schliessen()
        self._letzter_pdf_pfad = None
        self._ungespeicherte_aenderungen = False

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        if not self._ungespeicherte_aenderungen_bestaetigen(
            self.tr("Ungespeicherte Änderungen"),
            self.tr("Es gibt ungespeicherte Änderungen. Trotzdem beenden?"),
        ):
            event.ignore()
            return
        event.accept()

    def _speichern(self) -> None:
        if self._letzter_pdf_pfad is None:
            self._speichern_unter()
            return
        self._pdf_schreiben(self._letzter_pdf_pfad)

    def _speichern_unter(self) -> None:
        vorschlag = self._liste.dateiname_vorschlag() or self.tr("dokument.pdf")
        ziel = speichern_dialog(self, self.tr("PDF speichern unter"), vorschlag, self.tr("PDF-Datei (*.pdf)"))
        if ziel is None:
            return
        self._letzter_pdf_pfad = ziel
        self._pdf_schreiben(self._letzter_pdf_pfad)

    def _pdf_schreiben(self, ziel: Path) -> None:
        seiten = self._liste.seiten()
        if not seiten:
            QMessageBox.information(self, self.tr("Keine Seiten"), self.tr("Die Dateiliste ist leer."))
            return
        anzeige = Fortschrittsanzeige(self, self.tr("PDF wird erstellt …"), len(seiten))
        try:
            export_pdf(seiten, ziel, fortschritt=anzeige.callback,
                      dokument_metadaten=self._liste.pdf_metadaten_felder())
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Speichern fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        self._ungespeicherte_aenderungen = False

        # DE: "Speichern" ueberschreibt haeufig direkt die Datei, aus der
        #     die Seiten selbst stammen (z. B. bei einer frisch geoeffneten
        #     Einzeldatei, siehe _dokument_geoeffnet). Drehung/Spiegelung/
        #     Schwaerzung/Teilung sind dabei in export_pdf schon fest in die
        #     neuen Pixel eingebrannt worden -- die WorkingPage-Felder
        #     selbst (z. B. rotation) bleiben aber unveraendert auf ihrem
        #     alten Wert stehen. Ohne diesen Neuaufbau wuerde jede weitere
        #     Aktion, die die Seite aus ihrer Quelle neu rendert (z. B. ein
        #     Werkzeugwechsel), Drehung/Spiegelung/Schwaerzung ein ZWEITES
        #     Mal anwenden -- genau der vom Nutzer beobachtete Fehler
        #     (Seite nach Speichern+Zuschneiden wieder schief). Die Liste
        #     wird deshalb aus der frisch geschriebenen Datei neu aufgebaut,
        #     genau wie beim Schliessen und Neuoeffnen dieser Datei -- als
        #     EIN Rueckgaengig-Schritt, mit erhaltener aktueller Zeile.
        # EN: "Save" frequently overwrites the very file the pages
        #     themselves came from (e.g. a freshly opened single file, see
        #     _dokument_geoeffnet). Rotation/mirroring/redaction/splitting
        #     have already been baked into the new pixels by export_pdf --
        #     but the WorkingPage fields themselves (e.g. rotation) stay at
        #     their old value. Without this rebuild, any further action
        #     that re-renders the page from its source (e.g. switching
        #     tools) would apply rotation/mirroring/redaction a SECOND time
        #     -- exactly the bug the user observed (page skewed again
        #     after Save+Crop). The list is therefore rebuilt from the
        #     freshly written file, exactly like closing and reopening it
        #     -- as ONE undo step, with the current row preserved.
        if any(wp.source.path == ziel for wp in seiten):
            aktuelle_zeile = self._liste.currentRow()
            alle_eintraege = [self._liste.item(i) for i in range(self._liste.count())]
            neue_quellen = datei_aufschluesseln(ziel)
            self._liste.mehrere_ersetzen(alle_eintraege, neue_quellen)
            if 0 <= aktuelle_zeile < self._liste.count():
                self._liste.setCurrentRow(aktuelle_zeile)

        QMessageBox.information(self, self.tr("Gespeichert"), self.tr("PDF gespeichert unter:\n{0}").format(ziel))
