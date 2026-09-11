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
echo "Erzeuge .spec-Datei ..."
# DE: Erst nur die .spec-Datei erzeugen (nicht direkt bauen), damit wir
#     CFBundleDocumentTypes ergaenzen koennen -- dafuer gibt es keine
#     PyInstaller-Kommandozeilenoption, nur den info_plist-Parameter im
#     BUNDLE()-Aufruf der .spec-Datei. Damit merkt sich macOS, dass diese
#     App PDF- und Bilddateien oeffnen kann (taucht in "Öffnen mit" auf
#     und bleibt dort gemerkt) -- LSHandlerRank "Alternate" beansprucht
#     dabei NICHT automatisch die Standard-App-Rolle, das bleibt eine
#     bewusste Entscheidung des Nutzers in den Finder-Einstellungen.
# EN: First only generate the .spec file (don't build directly yet), so
#     we can add CFBundleDocumentTypes -- there's no PyInstaller
#     command-line option for that, only the info_plist parameter in the
#     .spec file's BUNDLE() call. This makes macOS remember that this
#     app can open PDF and image files (shows up in "Open With" and
#     stays remembered there) -- LSHandlerRank "Alternate" deliberately
#     does NOT claim the default-app role automatically, that stays the
#     user's own choice in Finder's settings.
pyi-makespec --windowed --name "$APPNAME" \
  --osx-bundle-identifier de.telefonanleitungen.pdfkrams \
  --add-data "pdfkrams/uebersetzungen:pdfkrams/uebersetzungen" \
  --add-data "pdfkrams/hilfe:pdfkrams/hilfe" \
  --add-data "pdfkrams/logo:pdfkrams/logo" \
  pdfkrams/main.py

python3 - "$APPNAME.spec" <<'PYEOF'
import sys

pfad = sys.argv[1]
with open(pfad, encoding="utf-8") as f:
    inhalt = f.read()

info_plist = """    info_plist={
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'PDF-Dokument',
                'LSItemContentTypes': ['com.adobe.pdf'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
            },
            {
                'CFBundleTypeName': 'Bilddatei',
                'LSItemContentTypes': [
                    'public.jpeg', 'public.png', 'public.tiff', 'com.microsoft.bmp',
                ],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
            },
        ],
    },
"""

marker = "bundle_identifier='de.telefonanleitungen.pdfkrams',"
if marker not in inhalt:
    raise SystemExit(f"Erwartete Zeile nicht gefunden in {pfad} -- PyInstaller-Spec-Format geaendert?")
inhalt = inhalt.replace(marker, marker + "\n" + info_plist)

with open(pfad, "w", encoding="utf-8") as f:
    f.write(inhalt)
print(f"CFBundleDocumentTypes in {pfad} ergaenzt.")
PYEOF

echo
echo "Baue die App ..."
pyinstaller --noconfirm "$APPNAME.spec"

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
