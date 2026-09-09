"""
DE: Kleine Fortschrittsanzeige fuer laengere Vorgaenge (Export, Dateien
    laden, Heftseiten verarbeiten). Die App arbeitet synchron auf dem
    GUI-Thread; ein regelmaessiges processEvents() waehrend des Vorgangs
    haelt das Fenster reaktionsfaehig und die Anzeige sichtbar aktuell --
    fuer die Groessenordnung dieser App (einzelne Sekunden bis wenige
    Minuten) reicht das, ohne die Komplexitaet eines eigenen
    Hintergrundthreads samt Thread-Sicherheit fuer Pillow/PyMuPDF.

EN: Small progress indicator for longer operations (export, loading files,
    processing booklet pages). The app works synchronously on the GUI
    thread; calling processEvents() periodically during the operation
    keeps the window responsive and the display visibly current -- for
    the scale of this app (a few seconds to a few minutes) that's enough,
    without the complexity of a dedicated background thread plus thread
    safety for Pillow/PyMuPDF.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QProgressDialog, QWidget


class Abgebrochen(Exception):
    """DE: Wird ausgeloest, wenn der Nutzer die Fortschrittsanzeige abbricht.
    EN: Raised when the user cancels the progress dialog."""


class Fortschrittsanzeige:
    """
    DE: Zeigt einen Fortschrittsdialog und liefert eine `callback`-Methode,
        die an lange laufende Kernfunktionen (export_pdf usw.) als
        `fortschritt`-Parameter uebergeben werden kann. Bei sehr kurzen
        Vorgaengen erscheint der Dialog gar nicht erst (setMinimumDuration).

    EN: Shows a progress dialog and provides a `callback` method that can
        be passed to long-running core functions (export_pdf etc.) as the
        `fortschritt` parameter. For very short operations the dialog
        doesn't even appear (setMinimumDuration).
    """

    def __init__(self, parent: QWidget | None, titel: str, gesamt: int) -> None:
        abbrechen_text = QCoreApplication.translate("Fortschrittsanzeige", "Abbrechen")
        self._titel = titel
        self._dialog = QProgressDialog("", abbrechen_text, 0, max(gesamt, 1), parent)
        self._dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._dialog.setMinimumDuration(400)
        self._dialog.setAutoClose(True)
        self._text_aktualisieren(0, gesamt)
        self._dialog.setValue(0)

    def _text_aktualisieren(self, erledigt: int, gesamt: int) -> None:
        # DE: Zaehlstand ("N von M") explizit im Text ergaenzen -- der
        #     Balken allein zeigt nur den Anteil, nicht die konkreten
        #     Stueckzahlen, nach denen aber oft gefragt wird.
        # EN: Explicitly add the count ("N of M") to the text -- the bar
        #     alone only shows the proportion, not the concrete item
        #     counts, which are often what people actually want to see.
        text = QCoreApplication.translate("Fortschrittsanzeige", "{0} ({1} von {2})").format(
            self._titel, erledigt, gesamt
        )
        self._dialog.setLabelText(text)

    def callback(self, erledigt: int, gesamt: int) -> None:
        """DE: An Kernfunktionen als `fortschritt`-Parameter uebergeben.
        EN: Pass to core functions as the `fortschritt` parameter."""
        self._dialog.setMaximum(max(gesamt, 1))
        self._dialog.setValue(erledigt)
        self._text_aktualisieren(erledigt, gesamt)
        QApplication.processEvents()
        if self._dialog.wasCanceled():
            raise Abgebrochen()

    def schliessen(self) -> None:
        self._dialog.reset()
