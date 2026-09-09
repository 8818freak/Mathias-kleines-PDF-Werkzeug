#!/bin/bash
# DE: Baut die eigenstaendige macOS-App "Mathias kleines PDF-Werkzeug.app" samt
#     .dmg zum Weitergeben. Einmal im Terminal ausfuehren:
#         chmod +x build_mac.sh && ./build_mac.sh
#     Kein Python wird auf dem Zielrechner benoetigt, die App ist vollstaendig
#     eigenstaendig. Der interne Name ist bewusst OHNE Apostroph (siehe
#     build_windows.bat fuer den Hintergrund) -- der Fenstertitel/Ueber-Dialog
#     im Programm selbst zeigt weiterhin ganz normal "Mathias' kleines
#     PDF-Werkzeug" mit Apostroph.
#
# EN: Builds the standalone macOS app "Mathias kleines PDF-Werkzeug.app"
#     plus a .dmg for sharing. Run once from the terminal:
#         chmod +x build_mac.sh && ./build_mac.sh
#     No Python is needed on the target machine, the app is fully
#     self-contained. The internal name deliberately has NO apostrophe (see
#     build_windows.bat for why) -- the program's own window title/About
#     dialog still shows the normal "Mathias' kleines PDF-Werkzeug" with the
#     apostrophe.

set -euo pipefail
cd "$(dirname "$0")"

APPNAME="Mathias kleines PDF-Werkzeug"

echo "Lege virtuelle Umgebung an ..."
python3 -m venv .venv
source .venv/bin/activate

echo
echo "Installiere Abhaengigkeiten ..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo
echo "Baue die App ..."
pyinstaller --windowed --name "$APPNAME" \
  --osx-bundle-identifier de.telefonanleitungen.pdfkrams \
  --add-data "pdfkrams/uebersetzungen:pdfkrams/uebersetzungen" \
  --noconfirm \
  pdfkrams/main.py

echo
echo "Baue das .dmg ..."
rm -rf "dist/dmg_tmp"
mkdir -p "dist/dmg_tmp"
cp -R "dist/$APPNAME.app" "dist/dmg_tmp/"
ln -s /Applications "dist/dmg_tmp/Applications"
hdiutil create -volname "$APPNAME" \
  -srcfolder "dist/dmg_tmp" \
  -ov -format UDZO \
  "dist/$APPNAME.dmg"
rm -rf "dist/dmg_tmp"

echo
echo "Fertig! Die App liegt in:"
echo "dist/$APPNAME.app"
echo "dist/$APPNAME.dmg"
