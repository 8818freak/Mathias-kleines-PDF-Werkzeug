"""
DE: Gemeinsame Export-Routine "aktuelle Seitenliste als eine PDF-Datei
    speichern" -- von mehreren Werkzeugen (PDF erstellen, Seiten drehen,
    Seiten teilen, Seiten nummerieren) fast identisch benutzt. An einer
    Stelle gebuendelt, damit das Speicherort-Merken (siehe datei_dialoge)
    und die Rueckmeldung an das Hauptfenster (PageListWidget.
    alsExportiertMarkiert, damit "Speichern"/Cmd+S danach dieselbe Datei
    trifft) nicht in jedem Werkzeug einzeln nachgezogen werden muessen.

    Die Texte (Titel, Vorschlag, Meldungen) werden bewusst als Parameter
    uebergeben statt hier selbst uebersetzt zu werden -- so bleibt jeder
    Aufrufer fuer pyside6-lupdate im eigenen Klassen-Kontext, und
    bestehende Uebersetzungen in der .ts-Datei bleiben gueltig.

EN: Shared export routine "save the current page list as one PDF file" --
    used almost identically by several tools (Create PDF, Rotate pages,
    Split pages, Number pages). Bundled in one place so remembering the
    save folder (see datei_dialoge) and reporting back to the main window
    (PageListWidget.alsExportiertMarkiert, so "Save"/Cmd+S afterward
    targets the same file) don't have to be repeated in every tool.

    Text (title, suggestion, messages) is deliberately passed in as
    parameters instead of being translated here -- that way every caller
    stays in its own class context for pyside6-lupdate, and existing
    translations in the .ts file remain valid.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from pdfkrams.core.combine import export_pdf
from pdfkrams.gui.widgets.datei_dialoge import speichern_dialog
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget


def seitenliste_als_pdf_exportieren(
    parent: QWidget,
    liste: PageListWidget,
    *,
    dialog_titel: str,
    dateiname_vorschlag: str,
    dialog_filter: str,
    fortschritt_text: str,
    fehler_titel: str,
    erfolg_titel: str,
    erfolg_text_vorlage: str,
) -> None:
    """DE: Fragt einen Zielpfad ab und schreibt die komplette aktuelle
        Seitenliste als eine PDF-Datei dorthin -- inklusive Fortschritts-
        anzeige, Fehlerbehandlung und Erfolgsmeldung.
    EN: Asks for a target path and writes the entire current page list
        there as one PDF file -- including progress display, error
        handling, and a success message."""
    ziel = speichern_dialog(parent, dialog_titel, dateiname_vorschlag, dialog_filter)
    if ziel is None:
        return
    seiten = liste.seiten()
    anzeige = Fortschrittsanzeige(parent, fortschritt_text, len(seiten))
    try:
        export_pdf(seiten, ziel, fortschritt=anzeige.callback)
    except Abgebrochen:
        return
    except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
        QMessageBox.critical(parent, fehler_titel, str(exc))
        return
    finally:
        anzeige.schliessen()
    QMessageBox.information(parent, erfolg_titel, erfolg_text_vorlage.format(ziel))
    liste.alsExportiertMarkiert.emit(ziel)
