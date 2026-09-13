"""
DE: Eine (potenziell laenger dauernde) Funktion in einem Hintergrund-
    Thread ausfuehren, waehrend im Vordergrund ein Fortschrittsdialog
    angezeigt wird. Wichtig fuer Vorgaenge, die aus EINEM einzelnen,
    nicht unterteilbaren Bibliotheksaufruf bestehen (z. B. eine PDF-Datei
    strukturell komprimieren oder mit PDF/A-Metadaten versehen) -- bei
    solchen Vorgaengen kann man nicht zwischendurch `processEvents()`
    aufrufen, weil es kein "zwischendurch" gibt. Blockiert der GUI-Thread
    laenger als ein paar Sekunden, ohne Ereignisse zu verarbeiten, haelt
    macOS die App faelschlich fuer abgestuerzt ("Nicht reagiert",
    Ladebalken-Cursor) und graut das Fenster aus, obwohl im Hintergrund
    alles normal weiterlaeuft. Der einzige zuverlaessige Ausweg: die
    eigentliche Arbeit in einen anderen Thread verlagern, damit die
    Qt-Ereignisschleife im Hauptthread frei bleibt.

EN: Run a (potentially long-running) function in a background thread
    while showing a progress dialog in the foreground. Important for
    operations that consist of ONE single, indivisible library call (e.g.
    structurally compressing a PDF file or adding PDF/A metadata) -- for
    such operations there's no "in between" at which to call
    `processEvents()`. If the GUI thread blocks for more than a couple of
    seconds without processing events, macOS wrongly considers the app
    crashed ("Not Responding", spinning cursor) and greys out the window,
    even though everything behind the scenes is proceeding normally. The
    only reliable way out: move the actual work to another thread, so the
    Qt event loop on the main thread stays free.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QCoreApplication, QObject, Qt, QThread, Signal
from PySide6.QtWidgets import QProgressDialog, QWidget


class _Worker(QObject):
    fortschritt = Signal(int, int)
    fertig = Signal(object)
    fehler = Signal(Exception)

    def __init__(self, funktion: Callable) -> None:
        super().__init__()
        self._funktion = funktion

    def start(self) -> None:
        try:
            ergebnis = self._funktion(lambda erledigt, gesamt: self.fortschritt.emit(erledigt, gesamt))
        except Exception as exc:  # noqa: BLE001 -- an den Aufrufer im Hauptthread weiterreichen
            self.fehler.emit(exc)
        else:
            self.fertig.emit(ergebnis)


def im_hintergrund_ausfuehren(parent: QWidget, titel: str, funktion: Callable):
    """
    DE: `funktion(fortschritt_callback)` in einem Hintergrund-Thread
        ausfuehren, waehrend `titel` in einem Fortschrittsdialog angezeigt
        wird -- unbestimmt (Balken laeuft ohne Prozentangabe), solange
        `funktion` den Callback nicht selbst mit konkreten Werten aufruft.
        `funktion` darf KEINE Qt-Widgets anfassen (laeuft in einem anderen
        Thread), dafuer aber beliebig lange dauern, ohne dass die App als
        abgestuerzt erscheint. Liefert das Ergebnis von `funktion` oder
        loest eine darin aufgetretene Ausnahme im Hauptthread erneut aus.

    EN: Run `funktion(fortschritt_callback)` in a background thread while
        showing `titel` in a progress dialog -- indeterminate (spinning,
        no percentage) unless `funktion` itself calls the callback with
        concrete values. `funktion` must NOT touch Qt widgets (runs on a
        different thread), but may take arbitrarily long without the app
        appearing to have crashed. Returns `funktion`'s result, or
        re-raises an exception it raised, on the main thread.
    """
    dialog = QProgressDialog(titel, None, 0, 0, parent)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setCancelButton(None)
    dialog.setMinimumDuration(0)

    thread = QThread(parent)
    worker = _Worker(funktion)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)

    ergebnis_box: dict = {}

    def bei_fortschritt(erledigt: int, gesamt: int) -> None:
        if gesamt > 0:
            dialog.setMaximum(gesamt)
            dialog.setValue(erledigt)
            dialog.setLabelText(
                QCoreApplication.translate("Fortschrittsanzeige", "{0} ({1} von {2})").format(
                    titel, erledigt, gesamt
                )
            )

    def bei_fertig(ergebnis) -> None:
        ergebnis_box["wert"] = ergebnis
        thread.quit()

    def bei_fehler(exc: Exception) -> None:
        ergebnis_box["fehler"] = exc
        thread.quit()

    worker.fortschritt.connect(bei_fortschritt)
    worker.fertig.connect(bei_fertig)
    worker.fehler.connect(bei_fehler)
    thread.finished.connect(dialog.close)

    thread.start()
    # DE: exec() startet eine verschachtelte Qt-Ereignisschleife -- das
    #     Fenster bleibt dadurch bedienbar/neu zeichenbar, waehrend die
    #     eigentliche Arbeit im Hintergrund-Thread laeuft.
    # EN: exec() starts a nested Qt event loop -- this keeps the window
    #     responsive/repaintable while the actual work runs on the
    #     background thread.
    dialog.exec()
    thread.wait()
    worker.deleteLater()
    thread.deleteLater()

    if "fehler" in ergebnis_box:
        raise ergebnis_box["fehler"]
    return ergebnis_box.get("wert")


def im_hintergrund_still_ausfuehren(
    parent: QObject, funktion: Callable, bei_fertig: Callable, bei_fehler: Callable | None = None,
) -> None:
    """
    DE: Wie im_hintergrund_ausfuehren(), aber OHNE Fortschrittsdialog und
        OHNE zu blockieren -- fuer beilaeufige Hintergrundarbeit, bei der
        die Oberflaeche normal weiter bedienbar bleiben soll (z. B. eine
        stille Update-Pruefung beim Programmstart, siehe
        core/update_check.py). `bei_fertig(ergebnis)` bzw. `bei_fehler(exc)`
        werden im Hauptthread aufgerufen, sobald `funktion` (die KEINE
        Qt-Widgets anfassen darf) fertig ist; ohne `bei_fehler` werden
        Fehler stillschweigend verworfen (fuer beilaeufige Arbeit wie eine
        Update-Pruefung angemessen -- kein Netz/kein GitHub erreichbar soll
        nicht mit einer Fehlermeldung stoeren).

    EN: Like im_hintergrund_ausfuehren(), but WITHOUT a progress dialog and
        WITHOUT blocking -- for incidental background work where the UI
        should stay normally usable (e.g. a silent update check on program
        startup, see core/update_check.py). `bei_fertig(ergebnis)` resp.
        `bei_fehler(exc)` are called on the main thread once `funktion`
        (which must NOT touch Qt widgets) is done; without `bei_fehler`,
        errors are silently discarded (appropriate for incidental work
        like an update check -- no network/no GitHub reachable shouldn't
        interrupt with an error message).
    """
    thread = QThread(parent)
    worker = _Worker(funktion)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)

    # DE: OHNE eine gehaltene Python-Referenz sammelt Pythons Garbage
    #     Collector thread/worker oft schon ein, bevor der Hintergrund-
    #     Thread ueberhaupt fertig ist -- der Qt-Elternbezug (parent)
    #     allein reicht dafuer nicht zuverlaessig aus (PySide6-Eigenheit).
    #     Ergebnis waere ein Absturz ("QThread: Destroyed while thread is
    #     still running"). Deshalb hier an einer Liste auf `parent`
    #     festgehalten, bis thread.finished feuert.
    # EN: WITHOUT a held Python reference, Python's garbage collector often
    #     collects thread/worker before the background thread is even
    #     done -- the Qt parent relationship alone isn't reliably enough
    #     (a PySide6 quirk). The result would be a crash ("QThread:
    #     Destroyed while thread is still running"). So it's kept alive
    #     here in a list on `parent` until thread.finished fires.
    if not hasattr(parent, "_stille_hintergrund_threads"):
        parent._stille_hintergrund_threads = []
    parent._stille_hintergrund_threads.append((thread, worker))

    def _aufraeumen() -> None:
        parent._stille_hintergrund_threads.remove((thread, worker))

    def _fertig(ergebnis) -> None:
        bei_fertig(ergebnis)
        thread.quit()

    def _fehler(exc: Exception) -> None:
        if bei_fehler is not None:
            bei_fehler(exc)
        thread.quit()

    worker.fertig.connect(_fertig)
    worker.fehler.connect(_fehler)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(_aufraeumen)
    thread.start()
