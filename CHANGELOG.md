# Änderungsprotokoll / Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier festgehalten.

*All notable changes to this project are documented here.*

## [1.2.1] – 2026-09-09

### Behoben / Fixed

- Übersetzungslücke in der Seitenliste: Hinweise wie „→ Ziel 3“ oder
  „horiz. gespiegelt“ blieben auf Englisch immer Deutsch, weil
  `pyside6-lupdate` den Text innerhalb der verwendeten Lambda-Hilfsfunktion
  nicht automatisch erkennen konnte. Fehlende Einträge von Hand ergänzt.
  *Translation gap in the page list: hints like "→ target 3" or "flipped
  horizontally" stayed German even in the English UI, because
  `pyside6-lupdate` couldn't automatically detect the text inside the
  lambda helper function used there. Missing entries added by hand.*
- Windows-Build robuster gemacht: Das Selbst-Update von `pip` schlug unter
  Windows zuverlässig fehl (`pip.exe` kann sich nicht selbst überschreiben,
  während es läuft); jetzt über `python -m pip` aufgerufen.
  *Windows build made more robust: `pip`'s self-update reliably failed on
  Windows (`pip.exe` can't overwrite itself while running); now invoked via
  `python -m pip`.*

## [1.2] – 2026-09-09

### Hinzugefügt / Added

- Mehrsprachige Oberfläche: Deutsch (Standard) und Englisch, umstellbar im
  neuen Einstellungen-Dialog (`Bearbeiten → Einstellungen …`). Ein
  Sprachwechsel wirkt sich nach einem Neustart des Programms aus.
  *Multilingual interface: German (default) and English, switchable in the
  new Preferences dialog (`Edit → Preferences …`). A language change takes
  effect after restarting the program.*
- Frei wählbare Maßeinheit (Millimeter/Zoll) für „Seitenmaß normieren“,
  wirkt sich sofort aus. Bewusst nicht an die Systemsprache/-region
  gekoppelt, da bearbeitete PDFs aus jedem Land stammen können.
  *Freely selectable measurement unit (millimeters/inches) for "Normalize
  page size", takes effect immediately. Deliberately not tied to the
  system language/region, since the PDFs being edited can come from any
  country.*
- „Seitenmaß normieren“ bietet zusätzlich US-Papierformate (Letter, Legal,
  Executive, Tabloid/Ledger) neben den DIN-A-Formaten — beide Formatgruppen
  stehen immer gleichzeitig zur Auswahl, unabhängig von der Maßeinheit.
  *"Normalize page size" additionally offers US paper formats (Letter,
  Legal, Executive, Tabloid/Ledger) alongside the DIN A formats — both
  format groups are always available at the same time, independent of the
  measurement unit.*

## [1.1] – 2026-09-09

### Hinzugefügt / Added

- Neues Werkzeug „Seiten zusammenfügen“: mehrere Teile (z. B. A4-Scans
  einer A1-Zeichnung) per Raster-Anordnung zu einer Seite verbinden, frei
  verschiebbar, mit Feindrehung und Randbeschnitt je Teil.
  *New "Combine pages" tool: merge several parts (e.g. A4 scans of an A1
  drawing) into one page via a grid layout, freely draggable, with a fine
  rotation and edge crop per part.*
- Neues Werkzeug „Seitenmaß normieren“: Seiten auf ein exaktes DIN-A-Format
  oder freies Maß in mm bringen, inklusive automatischer Erkennung und
  Abschneiden schwarzer Scan-Ränder sowie Größenvorschlag je Seite.
  *New "Normalize page size" tool: bring pages to an exact DIN A format or
  a free size in mm, including automatic detection and cropping of black
  scan borders as well as a per-page size suggestion.*

### Geändert / Changed

- `build_windows.bat` auf `--onefile` umgestellt (eine einzelne exe statt
  exe + separater `_internal`-Ordner, der sonst leicht für unwichtigen Kram
  gehalten und versehentlich gelöscht wird).
  *`build_windows.bat` switched to `--onefile` (a single exe instead of an
  exe plus a separate `_internal` folder, which otherwise easily looks like
  unimportant clutter and gets accidentally deleted).*

### Behoben / Fixed

- „Heftseiten teilen“: Der Überbreite-Dialog lief bisher, während die
  Fortschrittsanzeige noch offen war — deren Fenster-Modalität blockierte
  Eingaben für den gleichzeitig geöffneten Dialog. Alle interaktiven
  Abfragen laufen jetzt vollständig vor der Fortschrittsanzeige.
  *"Split booklet pages": the overwide-page dialog used to run while the
  progress dialog was still open — its window modality blocked input to
  the simultaneously open dialog. All interactive prompts now run
  completely before the progress dialog.*
- Über-Dialog: Copyright-Zeile und GPL-Gewährleistungsausschluss ergänzt
  (von der GPL-3.0 für interaktive Programme empfohlen).
  *About dialog: added a copyright line and the GPL warranty disclaimer
  (recommended by GPL-3.0 for interactive programs).*

## [1.0] – 2026-09-08

### Hinzugefügt / Added

- Erste Veröffentlichung: grafisches Werkzeug zum Nachbearbeiten
  gescannter Dokumente (macOS/Windows) mit den Werkzeugen PDF erstellen,
  Seiten drehen, Seiten teilen, Heftseiten automatisch neu ordnen, Seiten
  nummerieren, PDF in Bilder teilen, PDF verkleinern & PDF/A.
  *First release: a graphical tool for post-processing scanned documents
  (macOS/Windows) with the tools Create PDF, Rotate pages, Split pages,
  automatically reorder booklet pages, Number pages, Split PDF into
  images, Shrink PDF & PDF/A.*
