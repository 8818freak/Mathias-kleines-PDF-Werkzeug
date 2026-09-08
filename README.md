# Mathias' kleines PDF-Werkzeug

Eine grafische Anwendung zum Nachbearbeiten gescannter Dokumente -- für
macOS und Windows, ohne dass irgendein zusätzliches Programm installiert
werden muss.

*A graphical tool for post-processing scanned documents -- for macOS and
Windows, with no additional software to install.*

Kostenlos bereitgestellt von [Telefonanleitungen.de](https://www.telefonanleitungen.de).

![Screenshot](docs/screenshot.png)

## Funktionen / Features

- **PDF erstellen** -- PDF/JPG/BMP/TIF(F) (auch mehrseitige TIFFs) zu einer
  PDF-Datei zusammenfügen.
  *Combine PDF/JPG/BMP/TIF(F) files (including multi-page TIFFs) into one PDF.*
- **Seiten drehen** -- frei mit der Maus gerade ziehen, oder 90°/180°,
  Spiegeln, "abwechselnd drehen" für gescannte Doppelseiten.
  *Rotate pages freehand by dragging, or by 90°/180°, mirror, or
  alternate rotation for scanned spreads.*
- **Seiten teilen** -- beliebiges Raster aus Zeilen × Spalten, Schnittlinien
  mit der Maus ziehen, automatische Ausrichtung auf ruhige Bildbereiche.
  *Split a page into an arbitrary row × column grid, drag the cut lines by
  hand, with automatic alignment to quiet image areas.*
- **Heftseiten teilen** -- gescannte Doppelseiten aus gehefteten Broschüren
  automatisch in die richtige Reihenfolge bringen (inkl. überbreiter
  Umschlag-/Aufklappseiten).
  *Automatically reorder scanned saddle-stitch booklet spreads into the
  correct page sequence (including overwide cover/foldout pages).*
- **Seiten nummerieren** -- eine durcheinandergeratene Seitenfolge per
  Zielnummer neu anordnen, plus automatische Sortierung/Umbenennung nach
  Aufnahmedatum.
  *Rearrange a scrambled page sequence by assigning target numbers, plus
  automatic sorting/renaming by capture date.*
- **PDF in Bilder teilen** -- als einzelne durchnummerierte Bilddateien oder
  als eine mehrseitige TIFF-Datei exportieren.
  *Export as individually numbered image files or as one multi-page TIFF.*
- **PDF verkleinern & PDF/A** -- Dateigröße durch JPEG-Kodierung deutlich
  verringern (erkennt bereits effizient komprimierte Schwarzweißseiten und
  lässt sie unverändert), verlustfreie Struktur-Komprimierung, sowie
  PDF/A-2b-Kennzeichnung für die Archivierung.
  *Substantially shrink file size via JPEG encoding (detects already
  efficiently compressed black-and-white pages and leaves them untouched),
  lossless structural compression, and PDF/A-2b marking for archival.*

Alle Werkzeuge arbeiten auf derselben gemeinsamen Dateiliste -- einmal
laden, mit mehreren Werkzeugen nacheinander bearbeiten, ohne zwischendurch
exportieren zu müssen. Dazu: natives Menü mit Speichern/Speichern
unter/Rückgängig/Wiederholen, Fortschrittsanzeigen bei allen längeren
Vorgängen.

*All tools operate on the same shared file list -- load once, work through
several tools one after another without exporting in between. Plus: a
native menu with Save/Save As/Undo/Redo, and progress indicators for every
longer-running operation.*

## Installation

### Vorgefertigte Version / Pre-built version

Siehe [Releases](../../releases) für eine fertige macOS-App (.dmg) bzw.
Windows-exe, falls vorhanden.

*See [Releases](../../releases) for a ready-to-run macOS app (.dmg) or
Windows exe, if available.*

### Selbst bauen / Build from source

Voraussetzung: Python 3.11--3.13.

```bash
git clone <URL dieses Repositories>
cd app
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pdfkrams.main
```

Eine eigenständige App/exe bauen -- unter macOS `./build_mac.sh`, unter
Windows `build_windows.bat` per Doppelklick ausführen. Beide installieren
alle Abhängigkeiten automatisch in eine eigene virtuelle Umgebung und
bauen dann mit [PyInstaller](https://pyinstaller.org/).

*To build a standalone app/exe -- on macOS run `./build_mac.sh`, on
Windows double-click `build_windows.bat`. Both automatically install all
dependencies into their own virtual environment and then build with
[PyInstaller](https://pyinstaller.org/).*

## Technik / Tech stack

- [PySide6](https://pypi.org/project/PySide6/) (Qt für Python) -- Oberfläche
- [PyMuPDF](https://pypi.org/project/pymupdf/) -- PDF lesen/schreiben/rendern
- [Pillow](https://pypi.org/project/pillow/) -- Bildverarbeitung inkl. TIFF
- [pikepdf](https://pypi.org/project/pikepdf/) -- PDF/A-Metadaten

Bewusst ohne jede externe Kommandozeilen-Abhängigkeit (kein ImageMagick,
kein Ghostscript) -- alles reine Python-Bibliotheken, damit sich eine
vollständig eigenständige App/exe bauen lässt.

*Deliberately built without any external command-line dependency (no
ImageMagick, no Ghostscript) -- pure Python libraries only, so a fully
self-contained app/exe can be built.*

## Lizenz / License

[GNU General Public License v3.0](LICENSE)
