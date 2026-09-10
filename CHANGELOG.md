# Änderungsprotokoll / Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier festgehalten.

*All notable changes to this project are documented here.*

## [1.9] – 2026-09-11

### Hinzugefügt / Added

- Neues Werkzeug „Leerseiten entfernen“: sucht im gewählten Bereich nach
  wahrscheinlich leeren Seiten (per Tinte-Anteil) -- typisch beim
  automatisierten Scannen mit Einzug (unbedruckte Rückseiten, leere
  Trennblätter). Findet nur Vorschläge mit Häkchen zum Abwählen, löscht
  nichts automatisch.
  *New "Remove blank pages" tool: searches the selected scope for likely
  blank pages (via ink share) -- typical with automated ADF scanning
  (unprinted back sides, blank separator sheets). Only finds suggestions
  with checkboxes to deselect, doesn't delete anything automatically.*
- Neues Werkzeug „Schwärzen“: beliebig viele Bereiche einer Seite
  dauerhaft unkenntlich machen -- deckend gefüllte Rechtecke, frei mit
  der Maus gezeichnet, verschoben und in der Größe verändert, die beim
  Speichern wirklich in die Bildpixel eingebrannt werden (nicht nur
  optisch überdeckt). Betroffene Seiten werden dafür automatisch
  gerastert, auch wenn sie sonst verlustfrei als Vektorseite exportiert
  würden. Ein „Übertragen“-Knopf kopiert die Rechtecke einer Seite auf
  weitere -- praktisch für wiederkehrende Angaben (z. B. eine
  Aktennummer oben auf jeder Seite). Die Farbe ist in den Einstellungen
  wählbar (Standard: Schwarz).
  *New "Redact" tool: permanently obscure any number of areas on a page
  -- fully filled rectangles, freely drawn, moved, and resized with the
  mouse, which are actually burned into the image pixels on save (not
  just visually covered). Affected pages are automatically rasterized
  for this, even if they'd otherwise export losslessly as a vector page.
  A "Transfer" button copies one page's rectangles onto further pages --
  handy for recurring information (e.g. a case number at the top of
  every page). The color is selectable in Preferences (default: black).*

## [1.8] – 2026-09-11

### Hinzugefügt / Added

- „Datei → Datei schließen“ (Cmd+W bzw. Strg+W): leert die Dateiliste,
  ohne das Programm zu beenden -- fragt nach, falls es ungespeicherte
  Änderungen gibt. Dieselbe Rückfrage erscheint jetzt auch beim Beenden
  des Programms, falls ungespeicherte Änderungen vorliegen (gab es
  bisher gar nicht).
  *"File → Close file" (Cmd+W resp. Ctrl+W): clears the file list
  without quitting the program -- asks for confirmation if there are
  unsaved changes. The same confirmation now also appears when quitting
  the program if there are unsaved changes (didn't exist before at
  all).*
- Per Drag & Drop hinzugefügte Dateien lassen sich jetzt an einer
  bestimmten Stelle in die bereits geöffnete Dateiliste einfügen, statt
  immer nur ans Ende angehängt zu werden -- eine blaue Markierungslinie
  zeigt während des Ziehens, wo genau eingefügt würde.
  *Files added via drag & drop can now be inserted at a specific spot in
  the already-open file list, instead of always being appended at the
  end -- a blue marker line shows exactly where the insertion will land
  while dragging.*

## [1.7] – 2026-09-10

### Hinzugefügt / Added

- Neues Werkzeug „Lesezeichen setzen“: für Broschüren/Bücher jeder Seite
  optional einen Kapitel- oder Unterkapitel-Titel geben -- wird beim
  Speichern automatisch zu einem Lesezeichen/Inhaltsverzeichnis (Outline)
  in der PDF-Datei. Übersicht aller gesetzten Lesezeichen in
  Seitenreihenfolge, ein Klick springt zur jeweiligen Seite.
  *New "Set bookmarks" tool: for booklets/books, optionally give each
  page a chapter or sub-chapter title -- automatically becomes a
  bookmark/table of contents (outline) in the PDF file when saving.
  Overview of all bookmarks set so far in page order, click to jump to
  that page.*

## [1.6] – 2026-09-10

### Hinzugefügt / Added

- Neues Werkzeug „Metadaten bearbeiten“: dokumentweite PDF-Metadaten
  (Titel, Autor, Anbieter, Produkt, Version, Releasedatum, Stichwörter)
  -- anders als alle anderen Werkzeuge gilt das fürs gesamte Dokument,
  nicht pro Seite. Wird beim Speichern automatisch übernommen (Titel/
  Autor+Anbieter/Produkt/Version+Datum+Stichwörter fließen in die vier
  PDF-Standardfelder Titel/Autor/Thema/Stichwörter ein), inkl. einer
  Textvorschau. „Speichern unter“ schlägt daraus automatisch einen
  Dateinamen vor (z. B. „Gigaset E290 - Bedienungsanleitung v1.2
  (26-09).pdf“). Neue Einstellungen: Standard-Anbieter (fällt sonst auf
  den zuletzt verwendeten zurück) und Datumsformat fürs Releasedatum.
  *New "Edit metadata" tool: document-wide PDF metadata (title, author,
  provider, product, version, release date, keywords) -- unlike every
  other tool, this applies to the whole document, not per page. Applied
  automatically when saving (title/author+provider/product/version+date
  +keywords flow into the four standard PDF fields title/author/subject/
  keywords), including a text preview. "Save As" automatically suggests
  a filename built from these (e.g. "Gigaset E290 - Bedienungsanleitung
  v1.2 (26-09).pdf"). New preferences: default provider (falls back to
  the most recently used one otherwise) and date format for the release
  date.*

### Behoben / Fixed

- „PDF/A beim Export“ (im Werkzeug „PDF verkleinern & PDF/A“) schlug
  bislang immer fehl, da die PDF/A-Kennzeichnung dieselbe Datei, die
  gerade erst geschrieben wurde, direkt wieder überschreiben wollte --
  pikepdf verlangt dafür eine explizite Erlaubnis.
  *"PDF/A on export" (in the "Shrink PDF & PDF/A" tool) always failed,
  since PDF/A marking tried to overwrite the very file it had just
  written -- pikepdf requires explicit permission for that.*

## [1.5] – 2026-09-10

### Hinzugefügt / Added

- Neues Werkzeug „Bildbereinigung“: für gescannte Schwarzweiß-/
  Textvorlagen -- Binarisieren (Schwellwert, auf Wunsch automatisch per
  Otsu-Verfahren vorgeschlagen) und Despeckle (kleine dunkle Flecken/
  Staub entfernen), beide Schritte unabhängig voneinander zuschaltbar,
  mit Live-Vorschau. Binarisierte Seiten lassen sich anschließend in
  „PDF verkleinern & PDF/A“ oft deutlich kleiner komprimieren. Despeckle
  ist bewusst ohne die Abhängigkeit scipy umgesetzt (rein mit numpy), um
  die App schlank zu halten.
  *New "Image cleanup" tool: for scanned black-and-white/text originals
  -- binarizing (threshold, optionally auto-suggested via Otsu's method)
  and despeckling (removing small dark specks/dust), both steps
  independently toggleable, with a live preview. Binarized pages can
  often be compressed significantly smaller afterwards in "Shrink PDF &
  PDF/A". Despeckle is deliberately implemented without the scipy
  dependency (pure numpy), to keep the app lean.*

## [1.4] – 2026-09-09

### Hinzugefügt / Added

- „Seiten drehen“: neuer Knopf „Schräglage automatisch erkennen“ -- schlägt
  je Seite im gewählten Bereich per Projektionsprofil-Analyse (Textzeilen
  zu horizontalen Bändern verdichten) einen Geraderichtungswinkel vor und
  setzt ihn direkt, weiter von Hand nachjustierbar. Seiten ohne
  zuverlässig erkennbares Zeilenmuster (Fotos, grafiklastige Seiten)
  bleiben unverändert, mit Meldung am Ende. Neue Abhängigkeit: numpy (für
  die Bildanalyse).
  *"Rotate pages": new "Detect skew automatically" button -- suggests a
  straightening angle per page in the selected scope via projection-
  profile analysis (condensing text lines into horizontal bands) and sets
  it directly, still adjustable by hand afterward. Pages without a
  reliably detectable line pattern (photos, graphics-heavy pages) are
  left unchanged, with a report at the end. New dependency: numpy (for
  the image analysis).*

## [1.3] – 2026-09-09

### Hinzugefügt / Added

- Neues Werkzeug „Seiten zuschneiden“: Seiten von allen vier Rändern aus
  um ein frei wählbares Maß beschneiden (z. B. einen Lochrandstreifen
  oder Heftrand entfernen) -- anders als „Seitenmaß normieren“ ohne
  Skalierung, mit ziehbaren Linien in der Vorschau (der abgeschnittene
  Bereich wird abgedunkelt dargestellt) und Live-Anzeige der
  Ergebnisgröße inkl. Formatvorschlag.
  *New "Crop pages" tool: crop pages on all four edges by a freely
  chosen amount (e.g. to remove a punch-hole strip or binding margin) --
  unlike "Normalize page size", without scaling, with draggable lines in
  the preview (the cropped-away area is shown darkened) and a live
  display of the resulting size including a format suggestion.*
- Jede Fortschrittsanzeige zeigt jetzt zusätzlich "(N von M)" als Text an,
  nicht nur den Balken.
  *Every progress dialog now additionally shows "(N of M)" as text, not
  just the bar.*
- Hinweis zu Windows im Über-Dialog, README und allen Anleitungen: die
  Windows-Version wird vom Autor nicht selbst getestet, Fehlerberichte
  bitte an telefonmann@telefonanleitungen.de.
  *Note about Windows in the About dialog, README, and all manuals: the
  Windows version is not tested by the author, please report bugs to
  telefonmann@telefonanleitungen.de.*

### Behoben / Fixed

- Fortschrittsanzeigen ergänzt, wo sie bisher fehlten: „Seitenmaß
  normieren“, „Seiten zusammenfügen“, und beim eigentlichen Teilen bzw.
  automatischen Ausrichten in „Seiten teilen“.
  *Added progress dialogs where they were previously missing:
  "Normalize page size", "Combine pages", and the actual splitting resp.
  auto-alignment in "Split pages".*
- Der Ladefortschritt zählt jetzt Seiten statt Dateien -- bei einer
  einzelnen vielseitigen Datei (z. B. eine 900-seitige PDF) bewegte sich
  der Balken vorher die ganze Zeit nicht.
  *Loading progress now counts pages instead of files -- for a single
  many-page file (e.g. a 900-page PDF) the bar previously didn't move at
  all during the whole load.*
- Ein rein deutscher Kommentar (ohne EN-Übersetzung) in `page_list.py`
  ergänzt.
  *A German-only comment (missing its EN translation) in `page_list.py`
  completed.*

## [1.2.2] – 2026-09-09

### Behoben / Fixed

- „Öffnen mit …“ im Finder öffnete zwar die App, lud die gewünschte Datei
  aber nicht -- macOS übergibt sie als Apple-Event, nicht als
  Kommandozeilenargument, das wurde bisher gar nicht abgefangen. Betrifft
  jetzt auch den Fall, dass die App schon läuft. Unter Windows wird eine
  per Doppelklick/Dateizuordnung geöffnete Datei ebenfalls verarbeitet.
  *"Open With …" in Finder did open the app but never loaded the intended
  file -- macOS hands it over as an Apple Event, not a command-line
  argument, which wasn't being caught at all. Now also covers the case
  where the app is already running. On Windows, a file opened via
  double-click/file association is now handled as well.*
- „Speichern“ (Cmd+S) fragte immer nach einem Speicherort, selbst wenn
  genau eine bestehende PDF geöffnet wurde -- die App merkte sich nur
  Ziele aus „Speichern unter“. Wird jetzt beim Öffnen einer einzelnen PDF
  ebenfalls als Speicherziel übernommen; kommt eine weitere Datei hinzu,
  fragt „Speichern“ wieder nach, damit nichts versehentlich überschrieben
  wird.
  *"Save" (Cmd+S) always asked for a location, even when exactly one
  existing PDF had been opened -- the app only remembered targets from
  "Save As". Now also adopted as the save target when a single PDF is
  opened; once another file is added, "Save" asks again so nothing gets
  overwritten by accident.*

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
