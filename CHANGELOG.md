# Änderungsprotokoll / Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier festgehalten.

*All notable changes to this project are documented here.*

## [1.11.1] – 2026-09-12

### Behoben / Fixed

- Cmd+V/C/X/A funktionierte im Dateinamen-Feld der Speichern-/Öffnen-
  Dialoge weiterhin nicht richtig -- das native macOS-Panel liegt
  außerhalb der Qt-Kontrolle, und das in 1.10 ergänzte Bearbeiten-Menü
  fing das Tastenkürzel zwar ab ("es passiert etwas"), konnte es aber
  nicht ans native Feld weiterreichen. Alle Datei-Dialoge verwenden
  jetzt Qt's eigenen (nicht-nativen) Dialog, wodurch die Kürzel
  zuverlässig funktionieren.
  *Cmd+V/C/X/A still didn't work correctly in the filename field of
  Save/Open dialogs -- the native macOS panel lives outside Qt's
  control, and the Edit menu added in 1.10 intercepted the shortcut
  ("something happens") without being able to forward it to the native
  field. All file dialogs now use Qt's own (non-native) dialog, which
  makes the shortcuts work reliably.*
- Cmd+A ("Alles auswählen") wirkte in der gemeinsamen Seitenliste
  überhaupt nicht (z. B. im Werkzeug "Heftseiten teilen") -- derselbe
  Menü-Eintrag griff bisher nur bei Textfeldern. Wirkt jetzt zusätzlich
  auf die Seitenliste selbst.
  *Cmd+A ("Select All") had no effect at all in the shared page list
  (e.g. in the "Split booklet pages" tool) -- the same menu entry
  previously only worked on text fields. Now also acts on the page
  list itself.*

### Geändert / Changed

- Knöpfe und Gruppenrahmen sind app-weit kompakter (weniger
  Innenabstand) -- mehr Platz für Vorschau-/Arbeitsflächen, besonders
  spürbar bei "Seiten drehen" und "Seiten teilen". Dort außerdem zwei
  überlange Knopftexte gekürzt (Erklärung jetzt im Tooltip statt im
  Knopf selbst), da diese jeweils die Mindestbreite des ganzen
  Werkzeugs bestimmt hatten.
  *Buttons and group frames are more compact app-wide (less inner
  padding) -- more room for preview/work areas, especially noticeable
  in "Rotate pages" and "Split pages". Also shortened two overly long
  button labels there (explanation now in the tooltip instead of the
  button itself), since each had been dictating the whole tool's
  minimum width.*
- Anleitung/Hilfe: "Seitenmaß normieren" erklärt jetzt ausdrücklich,
  dass Hoch-/Querformat je Seite automatisch erkannt und beim Anwenden
  berücksichtigt werden (eine Datei mit gemischt hoch/quer gescannten
  Seiten lässt sich in einem Durchgang normieren).
  *Manual/help: "Normalize page size" now explicitly explains that
  portrait/landscape orientation is detected automatically per page
  and accounted for when applying (a file with a mix of portrait and
  landscape scans can be normalized in a single pass).*

## [1.11] – 2026-09-11

### Hinzugefügt / Added

- Neues Menü „Werkzeuge“ -- listet alle 17 Werkzeuge zusätzlich zur
  Seitenleiste zum Anklicken auf (mit Haken beim jeweils aktiven).
  *New "Tools" menu -- lists all 17 tools for clicking, in addition to
  the sidebar (with a checkmark on whichever is active).*
- Neues Menü „Ansicht“ mit „Werkzeugliste einblenden“ (Tastenkürzel
  F4) -- blendet die linke Seitenleiste aus/ein, um mehr Platz für
  Dateiliste und Werkzeugbereich zu schaffen; der Zustand wird über
  Programmstarts hinweg gemerkt.
  *New "View" menu with "Show tool list" (shortcut F4) -- hides/shows
  the left sidebar to make more room for the file list and tool area;
  the state is remembered across program launches.*

### Behoben / Fixed

- Die mittlere Spalte (Dateiliste) ließ sich über den Splitter kaum
  verschieben: `QStackedWidget` bemisst seine Mindestbreite
  standardmäßig am BREITESTEN aller enthaltenen Werkzeuge, auch
  unsichtbarer -- das breiteste Werkzeug blockierte dadurch den
  Splitter für alle anderen. Berichtet jetzt nur noch die Größe des
  aktuell sichtbaren Werkzeugs.
  *The middle column (file list) could barely be resized via the
  splitter: `QStackedWidget` sizes its minimum width from the WIDEST of
  all contained tools by default, even invisible ones -- the widest
  tool therefore blocked the splitter for every other tool. Now
  reports only the currently visible tool's size.*
- Die drei Knöpfe „Dateien hinzufügen …“/„Auswahl entfernen“/„Liste
  leeren“ oben in der Dateiliste standen in einer nicht umbrechenden
  Zeile und erzwangen dadurch selbst eine Mindestbreite der mittleren
  Spalte -- jetzt ein zweizeiliges Raster.
  *The three "Add files …"/"Remove selection"/"Clear list" buttons at
  the top of the file list sat in a non-wrapping row and thereby
  forced a minimum width on the middle column themselves -- now a
  two-row grid.*

## [1.10] – 2026-09-11

### Hinzugefügt / Added

- Neues Werkzeug „PDF reparieren & entsperren“, mit drei getrennten,
  unabhängig nutzbaren Funktionen:
  - **Reparieren:** rekonstruiert eine defekte Querverweistabelle bzw.
    einen fehlerhaften Dateiabschluss in einer PDF-Datei, die sich nicht
    mehr öffnen lässt (probiert dafür sowohl pikepdf/qpdf als auch
    PyMuPDF, je nachdem, welche Bibliothek mit dem konkreten Schaden
    zurechtkommt).
  - **Passwort entfernen:** entfernt den Passwortschutz einer Datei, wenn
    das Passwort bereits bekannt ist.
  - **Passwort wiederherstellen:** für ein wirklich vergessenes Passwort
    -- Wörterbuch-Angriff (eigenes Passwort-Log und/oder eine Wortliste)
    oder Brute-Force nach Zeichenart und Länge, mit vorheriger Schätzung
    von Kombinationsanzahl und Dauer sowie einem jederzeit wirksamen
    Abbrechen-Knopf.
  *New "Repair & unlock PDF" tool, with three separate, independently
  usable functions:*
  - *Repair: reconstructs a broken cross-reference table or a faulty
    file ending in a PDF file that can no longer be opened (tries both
    pikepdf/qpdf and PyMuPDF, depending on which library can handle the
    specific damage).*
  - *Remove password: removes a file's password protection when the
    password is already known.*
  - *Recover password: for a genuinely forgotten password -- dictionary
    attack (own password log and/or a wordlist) or brute force by
    character type and length, with an upfront estimate of the
    combination count and duration, plus a cancel button that always
    works.*
- Neues Werkzeug „Passwortschutz“, mit vier getrennten Funktionen, die
  sich eine gemeinsame Verschlüsselungseinstellung (Verfahren RC4/AES,
  Rechte-Passwort, Berechtigungen für Drucken/Kopieren/Bearbeiten)
  teilen:
  - **Einzelne Datei schützen:** ein Passwort zu einer einzelnen PDF
    hinzufügen.
  - **Ordner verschlüsseln:** alle PDF-Dateien in einem Ordner samt
    Unterordnern mit demselben Passwort direkt verschlüsseln.
  - **Nach Liste verschlüsseln:** Dateien anhand einer CSV-Liste
    (Dateipfad;Passwort) jeweils mit ihrem eigenen Passwort verschlüsseln.
  - **Passwort-Log:** merkt sich automatisch, welche Datei mit welchem
    Passwort versehen wurde -- Klartext, nur zur eigenen Ablage, als CSV
    export-/importierbar.
  *New "Password protection" tool, with four separate functions that
  share one set of encryption settings (RC4/AES method, permissions
  password, print/copy/edit permissions):*
  - *Protect a single file: add a password to a single PDF.*
  - *Encrypt folder: encrypt all PDF files in a folder, including
    subfolders, with the same password, directly.*
  - *Encrypt from list: encrypt files based on a CSV list (file
    path;password), each with its own password.*
  - *Password log: automatically remembers which file was given which
    password -- plaintext, for your own records only, exportable/
    importable as CSV.*
- Passwortfelder haben jetzt überall im Programm einen „anzeigen“-
  Umschalter zwischen verdecktem und Klartext-Passwort.
  *Password fields throughout the program now have a "show" toggle
  between masked and plaintext display.*
- „Seiten drehen“ wärmt beim Durchklicken die Vorschau der Nachbarseiten
  im Hintergrund vor -- spürbar flüssigeres Weiterblättern.
  *"Rotate pages" warms the preview of neighboring pages in the
  background while clicking through -- noticeably smoother paging.*
- Datei-Dialoge (Öffnen/Speichern/Ordner wählen) merken sich jetzt den
  zuletzt verwendeten Ordner, programmübergreifend.
  *File dialogs (open/save/choose folder) now remember the last-used
  folder, across the whole program.*
- Die Spaltenbreiten des Hauptfensters (Werkzeugliste/Dateiliste/
  Werkzeug-Bereich) werden zwischen Programmstarts gemerkt; die
  Trennlinie ist breiter (leichter zu treffen) und lässt sich nicht mehr
  versehentlich auf 0 zusammenziehen.
  *The main window's column widths (tool list/file list/tool area) are
  now remembered between launches; the divider is wider (easier to grab)
  and can no longer be accidentally collapsed to 0.*

### Behoben / Fixed

- Cmd+V (Einfügen) funktionierte in Textfeldern von Dialogen (z. B.
  einer Passwort-Abfrage) nicht -- nur Einfügen per Rechtsklick ging.
  Ursache: ohne ein Bearbeiten-Menü mit den Standard-Tastenkürzeln
  Ausschneiden/Kopieren/Einfügen/Alles auswählen registriert macOS diese
  Kürzel gar nicht erst.
  *Cmd+V (paste) didn't work in dialog text fields (e.g. a password
  prompt) -- only right-click paste worked. Cause: without an Edit menu
  registering the standard Cut/Copy/Paste/Select All shortcuts, macOS
  never registers them at all.*
- Nach einem Export über ein werkzeug-eigenes „Als PDF exportieren“
  (PDF erstellen, Seiten drehen, Seiten teilen, Seiten nummerieren)
  dachte das Hauptfenster weiterhin, es gäbe ungespeicherte Änderungen,
  und Cmd+S schrieb nicht in die gerade exportierte Datei, sondern fragte
  erneut nach einem Speicherort. Dasselbe machte „Datei schließen“
  (Cmd+W) unnötig oft nach ungespeicherten Änderungen zurückfragen.
  *After exporting via a tool's own "Export as PDF" button (Create PDF,
  Rotate pages, Split pages, Number pages), the main window kept
  thinking there were unsaved changes, and Cmd+S didn't write into the
  just-exported file but asked for a save location again. This also
  made "Close file" (Cmd+W) prompt about unsaved changes unnecessarily
  often.*
- Cmd+W schloss die Einstellungen und andere Dialogfenster nicht.
  *Cmd+W didn't close Preferences and other dialog windows.*
- Vorschau-Träge­heit beim Wechsel zwischen Seiten: alle acht Werkzeuge
  mit eigener großer Vorschau (Drehen, Zuschneiden, Schwärzen,
  Seitenmaß, Teilen, Nummerieren, Lesezeichen, Bildbereinigung)
  rendierten bei jedem Seitenwechsel mit, unabhängig davon, welches
  gerade sichtbar war -- bei vielen Seiten spürbar langsam.
  *Preview sluggishness when switching between pages: all eight tools
  with their own large preview (Rotate, Crop, Redact, Page size, Split,
  Number, Bookmarks, Image cleanup) re-rendered on every page change,
  regardless of which one was actually visible -- noticeably slow with
  many pages.*

## [1.9.1] – 2026-09-11

### Behoben / Fixed

- Wichtiger Fehler: Werkzeuge mit eigener Vorschau (Seiten zuschneiden,
  Bildbereinigung, Schwärzen, Seiten teilen, Seitenmaß normieren,
  Lesezeichen setzen, Seiten nummerieren, Seiten drehen) aktualisierten
  ihre Vorschau nur bei geänderter Seitenauswahl, nicht beim bloßen
  Wechsel zwischen Werkzeugen. Wer z. B. in „Seiten drehen“ geradezog und
  dann zu „Seiten zuschneiden“ wechselte, sah dort weiterhin die alte,
  schiefe Seite, bis eine andere Seite ausgewählt wurde.
  *Important bug: tools with their own preview (Crop pages, Image
  cleanup, Redact, Split pages, Normalize page size, Set bookmarks,
  Number pages, Rotate pages) only refreshed their preview when the page
  selection changed, not on a plain switch between tools. E.g. after
  straightening a page in "Rotate pages" and switching to "Crop pages",
  the old, skewed page kept showing there until a different page was
  selected.*

### Hinzugefügt / Added

- Seiten-Vorschau (Miniaturen und alle Werkzeug-Vorschauen) wird jetzt
  zwischengespeichert -- spürbar schnelleres Laden beim Wechseln
  zwischen Werkzeugen und Seiten, besonders bei vielseitigen Dokumenten.
  *Page previews (thumbnails and every tool's preview) are now cached --
  noticeably faster when switching between tools and pages, especially
  for many-page documents.*
- „Seiten drehen“: Zoom/Verschieben wie bei den anderen Werkzeugen
  (Strg/Cmd+Scrollen, Pinch-Geste), dichteres Referenzraster, jetzt auch
  mit senkrechten Linien (vorher nur waagerecht).
  *"Rotate pages": zoom/pan like the other tools (Ctrl/Cmd+scroll, pinch
  gesture), a tighter reference grid, now also with vertical lines
  (previously only horizontal).*
- „Seiten drehen“: die 90°-Schnelldrehung lässt sich jetzt auch per
  Cmd+L (linksherum) und Cmd+R (rechtsherum) auslösen.
  *"Rotate pages": the 90° quick rotation can now also be triggered via
  Cmd+L (counterclockwise) and Cmd+R (clockwise).*
- macOS merkt sich jetzt, dass das Programm PDF- und Bilddateien öffnen
  kann (taucht im Finder unter „Öffnen mit“ auf und bleibt dort
  gemerkt) -- unter Windows entsprechend über die Registry (nur für den
  aktuellen Nutzer, ungetestet auf echtem Windows).
  *macOS now remembers that the program can open PDF and image files
  (shows up in Finder's "Open With" and stays remembered there) --
  correspondingly via the registry on Windows (current user only,
  untested on real Windows).*
- Neuer Menüpunkt „Hilfe → Bedienungsanleitung“ (Cmd+? bzw. F1): öffnet
  die Anleitung in einem eigenen, durchsuchbaren Fenster (Cmd/Strg+F) --
  ohne externen PDF-Betrachter oder Browser, funktioniert identisch auf
  macOS und Windows.
  *New "Help → User Manual" menu item (Cmd+? resp. F1): opens the manual
  in its own searchable window (Cmd/Ctrl+F) -- no external PDF viewer or
  browser needed, works identically on macOS and Windows.*
- Logo von Telefonanleitungen.de im Über-Dialog, im Hilfe-Fenster und in
  den PDF-Anleitungen (nicht auf der Website-Fassung, dort ohnehin
  eindeutig).
  *Telefonanleitungen.de logo in the About dialog, the help window, and
  the PDF manuals (not on the website version, unambiguous there
  anyway).*

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
