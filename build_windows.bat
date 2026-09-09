@echo off
REM DE: Baut die eigenstaendige Windows-exe von "Mathias' kleines PDF-Werkzeug"
REM     als EINE EINZIGE Datei (--onefile) -- bewusst so gewaehlt, damit es
REM     sich wie die Mac-App verhaelt: eine Datei zum Weitergeben, kein
REM     zusaetzlicher Ordner mit Programmbibliotheken, den man leicht fuer
REM     unwichtigen Kram haelt und versehentlich loescht (im Gegensatz zur
REM     Mac-App sieht Windows von sich aus keine Buendel/Bundles vor -- der
REM     "onedir"-Modus wuerde exe + einen separaten _internal-Ordner nebenher
REM     erzeugen, die zusammenbleiben MUESSEN). Nachteil von --onefile: die
REM     exe startet minimal langsamer (packt sich beim Start kurz in einen
REM     Temp-Ordner aus).
REM     Einmal auf einem Windows-Rechner mit installiertem Python ausfuehren
REM     (Doppelklick oder in der Eingabeaufforderung). Das Ergebnis liegt
REM     danach in dist\Mathias kleines PDF-Werkzeug.exe -- kein Python und
REM     keine externen Programme werden auf dem Zielrechner benoetigt. Der
REM     interne Name ist bewusst OHNE Apostroph (PyInstaller erzeugt beim
REM     Bauen eine .spec-Datei als Python-Quellcode -- ein Apostroph im
REM     Namen bricht dort die Zeichenkette ab). Der Fenstertitel/Über-Dialog
REM     im Programm selbst zeigt weiterhin ganz normal "Mathias' kleines
REM     PDF-Werkzeug" mit Apostroph.
REM
REM EN: Builds the standalone Windows exe of "Mathias' kleines PDF-Werkzeug"
REM     as a SINGLE FILE (--onefile) -- deliberately chosen so it behaves
REM     like the Mac app: one file to hand over, no extra folder of program
REM     libraries that looks like unimportant clutter and gets accidentally
REM     deleted (unlike the Mac app, Windows has no native concept of
REM     bundles -- "onedir" mode would produce the exe plus a separate
REM     _internal folder alongside it, which MUST stay together). Downside
REM     of --onefile: the exe starts up very slightly slower (unpacks
REM     itself into a temp folder briefly on each launch).
REM     Run once on a Windows machine with Python installed (double-click
REM     or from the command prompt). The result ends up in
REM     dist\Mathias kleines PDF-Werkzeug.exe -- no Python and no external
REM     programs are needed on the target machine. The internal name
REM     deliberately has NO apostrophe (PyInstaller generates a .spec file
REM     as Python source code while building -- an apostrophe in the name
REM     breaks that string). The program's own window title/About dialog
REM     still shows the normal "Mathias' kleines PDF-Werkzeug" with the
REM     apostrophe.

setlocal enabledelayedexpansion
cd /d "%~dp0"

set APPNAME=Mathias kleines PDF-Werkzeug

echo Suche eine passende Python-Installation ...
set PYCMD=
for %%V in (3.13 3.12 3.11) do (
    if not defined PYCMD (
        py -%%V -c "print(1)" >nul 2>nul
        if not errorlevel 1 set PYCMD=py -%%V
    )
)
if not defined PYCMD (
    py -c "print(1)" >nul 2>nul
    if not errorlevel 1 set PYCMD=py
)
if not defined PYCMD (
    echo FEHLER: Keine passende Python-Installation gefunden.
    echo Bitte Python 3.11, 3.12 oder 3.13 von python.org installieren
    echo ^(Haekchen bei "Add python.exe to PATH" beim Setup setzen^).
    pause
    exit /b 1
)
echo Verwende: !PYCMD!

echo.
echo Lege virtuelle Umgebung an ...
!PYCMD! -m venv .venv_win
if not exist ".venv_win\Scripts\activate.bat" (
    echo FEHLER: Virtuelle Umgebung konnte nicht angelegt werden.
    pause
    exit /b 1
)
call .venv_win\Scripts\activate.bat

echo.
echo Installiere Abhaengigkeiten ...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo FEHLER: Installation der Abhaengigkeiten fehlgeschlagen.
    echo Haeufigste Ursache: keine Internetverbindung/DNS in dieser Shell
    echo ^(pruefen: im Browser https://pypi.org erreichbar?^). Falls ein
    echo Firmen-Proxy noetig ist: vorher z. B.
    echo   set HTTPS_PROXY=http://proxy.beispiel:8080
    echo setzen und das Skript erneut starten.
    pause
    exit /b 1
)
pip install pyinstaller
if errorlevel 1 (
    echo FEHLER: PyInstaller-Installation fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo Baue die exe ...
pyinstaller --onefile --windowed --name "%APPNAME%" --add-data "pdfkrams\uebersetzungen;pdfkrams\uebersetzungen" --noconfirm pdfkrams\main.py
if errorlevel 1 (
    echo.
    echo FEHLER: PyInstaller-Build fehlgeschlagen -- siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo Fertig! Die exe liegt in:
echo dist\%APPNAME%.exe
echo ^(genau diese EINE Datei enthaelt alles -- nichts anderes im dist-Ordner wird benoetigt^)
echo.
pause
