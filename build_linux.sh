#!/bin/bash
# DE: Baut ein eigenstaendiges Linux-Binary von "Mathias' kleines PDF-Werkzeug"
#     als EINE EINZIGE Datei (--onefile) -- selbes Prinzip wie
#     build_windows.bat, siehe dort fuer die ausfuehrliche Begruendung.
#     Einmal auf einem Linux-Rechner mit installiertem Python 3 ausfuehren:
#         chmod +x build_linux.sh && ./build_linux.sh
#     Das Ergebnis liegt danach in dist/Mathias kleines PDF-Werkzeug -- kein
#     Python wird auf dem Zielrechner benoetigt. Ungetestet in dieser
#     Entwicklungsumgebung (keine Linux-Maschine verfuegbar) -- der Code
#     selbst ist reines, plattformunabhaengiges Python + PySide6, alle
#     Abhaengigkeiten in requirements.txt gibt es als fertige Linux-Wheels
#     auf PyPI, insofern sollte nichts hier ueberraschen. Falls doch etwas
#     nicht klappt: am ehesten fehlende Systembibliotheken fuer Qt (z. B.
#     libxcb-cursor0, libEGL) -- die muessen ueber den Paketmanager der
#     jeweiligen Distribution nachinstalliert werden, PyInstaller kann sie
#     nicht mitbuendeln.
#
# EN: Builds a standalone Linux binary of "Mathias' kleines PDF-Werkzeug" as
#     a SINGLE FILE (--onefile) -- same principle as build_windows.bat, see
#     there for the full rationale. Run once on a Linux machine with Python
#     3 installed:
#         chmod +x build_linux.sh && ./build_linux.sh
#     The result ends up in dist/Mathias kleines PDF-Werkzeug -- no Python
#     is needed on the target machine. Untested in this development
#     environment (no Linux machine available) -- the code itself is plain,
#     platform-independent Python + PySide6, all dependencies in
#     requirements.txt have ready-made Linux wheels on PyPI, so nothing
#     here should be surprising. If something doesn't work: most likely
#     missing system libraries for Qt (e.g. libxcb-cursor0, libEGL) -- those
#     need to be installed via the distribution's own package manager,
#     PyInstaller cannot bundle them.

set -euo pipefail
cd "$(dirname "$0")"

APPNAME="Mathias kleines PDF-Werkzeug"

echo "Lege virtuelle Umgebung an ..."
python3 -m venv .venv_linux
source .venv_linux/bin/activate

echo
echo "Installiere Abhaengigkeiten ..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo
echo "Baue das Binary ..."
pyinstaller --onefile --windowed --name "$APPNAME" \
  --add-data "pdfkrams/uebersetzungen:pdfkrams/uebersetzungen" \
  --add-data "pdfkrams/hilfe:pdfkrams/hilfe" \
  --add-data "pdfkrams/logo:pdfkrams/logo" \
  --noconfirm pdfkrams/main.py

echo
echo "Fertig! Das Binary liegt in:"
echo "dist/$APPNAME"
echo "(genau diese EINE Datei enthaelt alles -- ausfuehrbar machen mit"
echo " chmod +x \"dist/$APPNAME\", falls noetig)"
