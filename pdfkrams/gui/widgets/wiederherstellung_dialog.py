"""
DE: Fortschrittsdialog fuer die Passwort-Wiederherstellung (siehe
    core/passwort_wiederherstellung.py) -- im Unterschied zu
    widgets/hintergrund.py's im_hintergrund_ausfuehren() MIT echtem
    Abbrechen-Knopf und einer live nachgefuehrten Restzeit-Schaetzung,
    weil ein Brute-Force-Lauf Stunden oder Tage dauern kann und der
    Nutzer ihn jederzeit stoppen koennen muss, nicht nur beim Start
    abbrechen kann.

EN: Progress dialog for password recovery (see
    core/passwort_wiederherstellung.py) -- unlike widgets/hintergrund.py's
    im_hintergrund_ausfuehren(), WITH a real cancel button and a live-
    updated remaining-time estimate, because a brute-force run can take
    hours or days and the user must be able to stop it at any point, not
    only decline before it starts.
"""

from __future__ import annotations

import time
from typing import Callable

from PySide6.QtCore import QCoreApplication, QObject, Qt, QThread, Signal
from PySide6.QtWidgets import QProgressDialog, QWidget


def dauer_text(sekunden: float) -> str:
    """DE: Sekunden in eine grob lesbare Dauer umwandeln (s/min/h/Tage).
    EN: Convert seconds into a roughly readable duration (s/min/h/days)."""
    if sekunden < 60:
        return QCoreApplication.translate("Wiederherstellung", "{0} s").format(round(sekunden))
    minuten = sekunden / 60
    if minuten < 60:
        return QCoreApplication.translate("Wiederherstellung", "{0} min").format(round(minuten))
    stunden = minuten / 60
    if stunden < 48:
        return QCoreApplication.translate("Wiederherstellung", "{0} Std.").format(round(stunden))
    return QCoreApplication.translate("Wiederherstellung", "{0} Tage").format(round(stunden / 24))


class _Worker(QObject):
    # DE: Signal(object, object) statt Signal(int, int) -- ein
    #     Brute-Force-Suchraum kann leicht die Grenze eines C++ "int"
    #     (32-Bit, ~2,1 Milliarden) ueberschreiten (z. B. schon Ziffern+
    #     Klein-/Grossbuchstaben bei Laenge 6). "object" gibt beliebig
    #     grosse Python-int-Werte unveraendert weiter.
    # EN: Signal(object, object) instead of Signal(int, int) -- a
    #     brute-force search space can easily exceed a C++ "int"'s
    #     32-bit range (~2.1 billion) (e.g. already digits+upper/
    #     lowercase letters at length 6). "object" passes arbitrarily
    #     large Python int values through unchanged.
    fortschritt = Signal(object, object)
    fertig = Signal(object)

    def __init__(self, funktion: Callable) -> None:
        super().__init__()
        self._funktion = funktion
        self._abbrechen_angefordert = False

    def abbrechen(self) -> None:
        # DE: Einfaches Bool-Flag statt QMutex -- wird nur gelesen/gesetzt,
        #     kein zusammengesetzter Zustand, in CPython durch die GIL
        #     ausreichend sicher fuer diesen simplen Fall.
        # EN: Simple bool flag instead of QMutex -- only read/set, no
        #     composite state, sufficiently safe under CPython's GIL for
        #     this simple case.
        self._abbrechen_angefordert = True

    def start(self) -> None:
        ergebnis = self._funktion(
            fortschritt=lambda erledigt, gesamt: self.fortschritt.emit(erledigt, gesamt),
            abbrechen=lambda: self._abbrechen_angefordert,
        )
        self.fertig.emit(ergebnis)


def wiederherstellung_ausfuehren(parent: QWidget, titel: str, funktion: Callable) -> tuple[str | None, bool]:
    """
    DE: `funktion(fortschritt, abbrechen)` (siehe core/passwort_
        wiederherstellung.py's woerterbuch_angriff/brute_force) in einem
        Hintergrund-Thread ausfuehren, mit Fortschrittsbalken, Restzeit-
        Schaetzung und echtem Abbrechen-Knopf. Liefert (gefundenes
        Passwort oder None, ob abgebrochen wurde).
    EN: Run `funktion(fortschritt, abbrechen)` (see core/passwort_
        wiederherstellung.py's woerterbuch_angriff/brute_force) on a
        background thread, with a progress bar, remaining-time estimate,
        and a real cancel button. Returns (found password or None,
        whether it was cancelled).
    """
    dialog = QProgressDialog(titel, QCoreApplication.translate("Wiederherstellung", "Abbrechen"), 0, 0, parent)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumDuration(0)

    thread = QThread(parent)
    worker = _Worker(funktion)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)

    zustand = {"start": time.monotonic(), "abgebrochen": False}
    # DE: Der Fortschrittsbalken selbst arbeitet mit einem festen 0..10000-
    #     Massstab statt mit den echten Zahlen -- ein Brute-Force-Suchraum
    #     kann leicht Milliarden Kombinationen umfassen, und
    #     QProgressDialog.setMaximum() ist (wie jedes Qt-Widget) ein
    #     C++ "int" (32-Bit, ~2,1 Milliarden Obergrenze). Die tatsaechlichen,
    #     beliebig grossen Zahlen stehen weiterhin im Text (dauerhaft
    #     als Python-int, ohne diese Grenze).
    # EN: The progress bar itself uses a fixed 0..10000 scale instead of
    #     the real numbers -- a brute-force search space can easily span
    #     billions of combinations, and QProgressDialog.setMaximum() is
    #     (like every Qt widget) a C++ "int" (32-bit, ~2.1 billion cap).
    #     The actual, arbitrarily large numbers still appear in the text
    #     (staying a Python int throughout, without that limit).
    _MASSSTAB = 10_000
    dialog.setMaximum(_MASSSTAB)

    def bei_fortschritt(erledigt: int, gesamt: int) -> None:
        if gesamt <= 0:
            return
        dialog.setValue(int(erledigt / gesamt * _MASSSTAB))
        vergangen = time.monotonic() - zustand["start"]
        rate = erledigt / vergangen if vergangen > 0 else 0
        rest = (gesamt - erledigt) / rate if rate > 0 else 0
        dialog.setLabelText(
            QCoreApplication.translate(
                "Wiederherstellung", "{0}\n{1} von {2} ({3} pro Sekunde) -- noch ca. {4}"
            ).format(titel, erledigt, gesamt, round(rate), dauer_text(rest))
        )

    ergebnis_box: dict = {}

    def bei_fertig(ergebnis) -> None:
        ergebnis_box["wert"] = ergebnis
        thread.quit()

    def bei_abbrechen() -> None:
        zustand["abgebrochen"] = True
        worker.abbrechen()

    worker.fortschritt.connect(bei_fortschritt)
    worker.fertig.connect(bei_fertig)
    dialog.canceled.connect(bei_abbrechen)
    # DE: reset() statt close() -- QProgressDialog.closeEvent() behandelt
    #     ein simples close() intern wie einen Klick auf "Abbrechen" und
    #     loest canceled() aus, was hier faelschlich als Nutzer-Abbruch
    #     durchgeschlagen waere, obwohl die Arbeit ganz normal fertig
    #     wurde. reset() blendet den Dialog ohne dieses Signal aus.
    # EN: reset() instead of close() -- QProgressDialog.closeEvent()
    #     internally treats a plain close() like a click on "Cancel" and
    #     emits canceled(), which would have wrongly registered here as a
    #     user cancellation even though the work finished normally.
    #     reset() hides the dialog without that signal.
    thread.finished.connect(dialog.reset)

    thread.start()
    dialog.exec()
    thread.wait()
    worker.deleteLater()
    thread.deleteLater()

    return ergebnis_box.get("wert"), zustand["abgebrochen"]
