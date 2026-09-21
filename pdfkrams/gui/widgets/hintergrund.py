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

from PySide6.QtCore import QCoreApplication, QObject, Qt, QThread, Signal, Slot
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

    # DE: Echtes QObject als Empfaenger statt einer simplen Python-Closure
    #     -- siehe die ausfuehrliche Begruendung bei _StillesEmpfangsobjekt
    #     weiter unten: nur so behandelt Qt die Verbindung zuverlaessig als
    #     QueuedConnection und ruft diese Methoden im Hauptthread auf, statt
    #     faelschlich im Hintergrund-Thread (der dort direkt angefasste
    #     `dialog` wuerde sonst von auesserhalb des Hauptthreads veraendert
    #     -- undefiniertes Verhalten unter Cocoa, im schlimmsten Fall ein
    #     Absturz).
    # EN: A real QObject as receiver instead of a plain Python closure --
    #     see the detailed rationale at _StillesEmpfangsobjekt below: only
    #     this way does Qt reliably treat the connection as a
    #     QueuedConnection and call these methods on the main thread,
    #     instead of wrongly on the background thread (the `dialog`
    #     touched there directly would otherwise be modified from outside
    #     the main thread -- undefined behavior under Cocoa, in the worst
    #     case a crash).
    class _Empfaenger(QObject):
        @Slot(int, int)
        def fortschritt(self, erledigt: int, gesamt: int) -> None:
            if gesamt > 0:
                dialog.setMaximum(gesamt)
                dialog.setValue(erledigt)
                dialog.setLabelText(
                    QCoreApplication.translate("Fortschrittsanzeige", "{0} ({1} von {2})").format(
                        titel, erledigt, gesamt
                    )
                )

        @Slot(object)
        def fertig(self, ergebnis) -> None:
            ergebnis_box["wert"] = ergebnis
            thread.quit()

        @Slot(Exception)
        def fehler(self, exc: Exception) -> None:
            ergebnis_box["fehler"] = exc
            thread.quit()

    empfaenger = _Empfaenger()
    worker.fortschritt.connect(empfaenger.fortschritt)
    worker.fertig.connect(empfaenger.fertig)
    worker.fehler.connect(empfaenger.fehler)
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


class _StillesEmpfangsobjekt(QObject):
    """
    DE: Reines Empfangsobjekt fuer worker.fertig/fehler, im Hauptthread
        erzeugt (im_hintergrund_still_ausfuehren wird immer vom
        Hauptthread aus aufgerufen). NOTWENDIG, damit Qt die Verbindung
        korrekt als QueuedConnection behandelt: Qt entscheidet
        Direct/Queued anhand der Thread-Zugehoerigkeit des EMPFAENGER-
        QObject -- bei einer Verbindung auf eine simple Python-Closure
        (kein QObject) fehlt dieser Bezug, Qt ruft die Closure dann
        DIREKT im Sender-Thread (dem Hintergrund-Thread) auf, statt sie
        sicher in den Hauptthread zu queuen. Faengt `bei_fertig`/
        `bei_fehler` also faelschlich im Hintergrund-Thread ab, statt im
        Hauptthread -- fatal, sobald diese Callbacks selbst GUI-Elemente
        anfassen (z. B. eine QMessageBox oeffnen): macOS stuerzt dann ab,
        weil ein natives Fenster ausserhalb des Hauptthreads erzeugt wird
        (reale Absturzursache der stillen Update-Pruefung).
    EN: Plain receiver object for worker.fertig/fehler, created on the
        main thread (im_hintergrund_still_ausfuehren is always called
        from the main thread). NECESSARY for Qt to treat the connection
        correctly as a QueuedConnection: Qt decides Direct/Queued based
        on the RECEIVER QObject's thread affinity -- a connection to a
        plain Python closure (not a QObject) has no such affinity to go
        by, so Qt calls the closure DIRECTLY on the sender's thread (the
        background thread) instead of safely queuing it to the main
        thread. This wrongly catches `bei_fertig`/`bei_fehler` on the
        background thread instead of the main thread -- fatal as soon as
        those callbacks themselves touch GUI elements (e.g. opening a
        QMessageBox): macOS then crashes because a native window gets
        created off the main thread (the real cause of the silent update
        check's crash).
    """

    def __init__(self, thread: QThread, bei_fertig: Callable, bei_fehler: Callable | None) -> None:
        super().__init__()
        self._thread = thread
        self._bei_fertig = bei_fertig
        self._bei_fehler = bei_fehler

    @Slot(object)
    def fertig(self, ergebnis) -> None:
        self._bei_fertig(ergebnis)
        self._thread.quit()

    @Slot(Exception)
    def fehler(self, exc: Exception) -> None:
        if self._bei_fehler is not None:
            self._bei_fehler(exc)
        self._thread.quit()


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
    empfaenger = _StillesEmpfangsobjekt(thread, bei_fertig, bei_fehler)

    if not hasattr(parent, "_stille_hintergrund_threads"):
        parent._stille_hintergrund_threads = []
    parent._stille_hintergrund_threads.append((thread, worker, empfaenger))

    def _aufraeumen() -> None:
        parent._stille_hintergrund_threads.remove((thread, worker, empfaenger))

    worker.fertig.connect(empfaenger.fertig)
    worker.fehler.connect(empfaenger.fehler)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(empfaenger.deleteLater)
    thread.finished.connect(_aufraeumen)
    thread.start()
