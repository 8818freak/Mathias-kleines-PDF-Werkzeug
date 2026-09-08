@echo off
REM DE: Baut die eigenstaendige Windows-exe von "Mathias' kleines PDF-Werkzeug".
REM     Einmal auf einem Windows-Rechner mit installiertem Python ausfuehren
REM     (Doppelklick oder in der Eingabeaufforderung). Das Ergebnis liegt danach
REM     in dist\Mathias kleines PDF-Werkzeug\Mathias kleines PDF-Werkzeug.exe --
REM     kein Python und keine externen Programme werden auf dem Zielrechner
REM     benoetigt, die exe ist vollstaendig eigenstaendig. Der interne Name ist
REM     bewusst OHNE Apostroph (PyInstaller erzeugt beim Bauen eine .spec-Datei
REM     als Python-Quellcode -- ein Apostroph im Namen bricht dort die
REM     Zeichenkette ab). Der Fenstertitel/Über-Dialog im Programm selbst zeigt
REM     weiterhin ganz normal "Mathias' kleines PDF-Werkzeug" mit Apostroph.
REM
REM EN: Builds the standalone Windows exe of "Mathias' kleines PDF-Werkzeug".
REM     Run once on a Windows machine with Python installed (double-click or
REM     from the command prompt). The result ends up in
REM     dist\Mathias kleines PDF-Werkzeug\Mathias kleines PDF-Werkzeug.exe --
REM     no Python and no external programs are needed on the target machine,
REM     the exe is fully self-contained. The internal name deliberately has
REM     NO apostrophe (PyInstaller generates a .spec file as Python source
REM     code while building -- an apostrophe in the name breaks that string).
REM     The program's own window title/About dialog still shows the normal
REM     "Mathias' kleines PDF-Werkzeug" with the apostrophe.

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
pyinstaller --windowed --name "%APPNAME%" --noconfirm pdfkrams\main.py
if errorlevel 1 (
    echo.
    echo FEHLER: PyInstaller-Build fehlgeschlagen -- siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo Fertig! Die exe liegt in:
echo dist\%APPNAME%\%APPNAME%.exe
echo.
pause
