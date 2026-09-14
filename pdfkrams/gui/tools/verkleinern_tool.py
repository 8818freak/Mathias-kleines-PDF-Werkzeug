"""
DE: Werkzeug "PDF verkleinern & PDF/A": exportiert die gemeinsame
    Seitenliste als deutlich kleinere PDF-Datei (JPEG-Kodierung statt
    verlustfrei, wählbare Qualität und Höchstauflösung -- bei gescannten
    Dokumenten typischerweise um ein Vielfaches kleiner) und kann jede
    PDF-Datei nachträglich mit den strukturellen Kennzeichen fürs
    Archivformat PDF/A-2b versehen (eingebettetes Farbprofil + passende
    Metadaten). Seiten, die bereits in einem Format vorliegen, bei dem
    JPEG-Neukodierung ueberwiegend keinen Sinn ergibt (JBIG2/CCITT fuer
    Schwarzweiss-/Strichinhalt, JPX/JPEG2000 fuer bereits effizient
    komprimierte Fotoseiten), werden unveraendert uebernommen -- der Knopf
    "Datei analysieren" zeigt vorab, wie viele Seiten das betrifft.

EN: "Shrink PDF & PDF/A" tool: exports the shared page list as a
    significantly smaller PDF file (JPEG encoding instead of lossless,
    selectable quality and maximum resolution -- for scanned documents
    typically many times smaller) and can retrofit any PDF file with the
    structural markers for the PDF/A-2b archival format (embedded color
    profile + matching metadata). Pages already stored in a format where
    JPEG re-encoding mostly doesn't make sense (JBIG2/CCITT for black-and-
    white/line content, JPX/JPEG2000 for already efficiently compressed
    photo pages) are carried over unchanged -- the "Analyze file" button
    shows in advance how many pages that affects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.document import WorkingPage, datei_aufschluesseln
from pdfkrams.core.komprimierung import (
    ausgangsgroesse_falls_eindeutig,
    codec_analyse,
    export_pdf_komprimiert,
    strukturell_komprimieren,
)
from pdfkrams.core.pdfa import als_pdfa_markieren
from pdfkrams.gui.widgets.batch_ziel_dialog import batch_ziel_dialog
from pdfkrams.gui.widgets.datei_dialoge import einzeln_oeffnen_dialog, oeffnen_dialog, speichern_dialog
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.hintergrund import im_hintergrund_ausfuehren
from pdfkrams.gui.widgets.page_list import PageListWidget


def _lesbare_groesse(bytes_anzahl: int) -> str:
    if bytes_anzahl >= 1_000_000:
        return f"{bytes_anzahl / 1_000_000:.1f} MB"
    return f"{bytes_anzahl / 1_000:.0f} KB"


class VerkleinernToolWidget(QWidget):
    """
    DE: GUI-Seite fuer verkleinerten Export und PDF/A-Kennzeichnung.
    EN: GUI page for shrunk export and PDF/A marking.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        # -- Dateigroesse verringern / reduce file size --------------------
        hinweis = QLabel(
            self.tr("Exportiert die Dateiliste links als deutlich kleinere PDF-Datei -- "
                   "jede Seite wird verlustbehaftet als JPEG statt verlustfrei "
                   "kodiert. Bei gescannten Dokumenten oft 10-100x kleiner. Nicht "
                   "geeignet für Seiten mit echtem Vektortext (der wird dabei zu "
                   "Pixeln). Bereits effizient komprimierte Seiten (z. B. JPEG2000- "
                   "oder JBIG2-Scans) werden unverändert übernommen, statt sie zu "
                   "JPEG umzukodieren -- das würde sie oft eher vergrößern als "
                   "verkleinern.")
        )
        hinweis.setWordWrap(True)

        einstellungen_zeile = QHBoxLayout()
        self._qualitaet_feld = QSpinBox()
        self._qualitaet_feld.setRange(1, 95)
        self._qualitaet_feld.setValue(75)
        self._qualitaet_feld.setPrefix(self.tr("JPEG-Qualität: "))
        self._qualitaet_feld.setSuffix(" %")

        self._dpi_aktiv_feld = QCheckBox(self.tr("Auflösung begrenzen auf"))
        self._dpi_aktiv_feld.setChecked(True)
        self._dpi_feld = QSpinBox()
        self._dpi_feld.setRange(50, 1200)
        self._dpi_feld.setValue(200)
        self._dpi_feld.setSuffix(" dpi")
        self._dpi_aktiv_feld.toggled.connect(self._dpi_feld.setEnabled)

        einstellungen_zeile.addWidget(self._qualitaet_feld)
        einstellungen_zeile.addWidget(self._dpi_aktiv_feld)
        einstellungen_zeile.addWidget(self._dpi_feld)

        self._pdfa_beim_export_feld = QCheckBox(self.tr("Zusätzlich als PDF/A-2b kennzeichnen"))

        # DE: Analyse VOR dem eigentlichen (bei vielen Seiten langwierigen)
        #     Export -- prueft, wie viele Seiten bereits in einem Format
        #     vorliegen (JBIG2/CCITT/JPX), bei dem JPEG-Neukodierung
        #     ueberwiegend keinen Sinn ergibt (siehe core/komprimierung.py's
        #     _bereits_effizient_komprimiert()). Genau der Fall, der einmal
        #     zu einer 912-seitigen Datei fuehrte, die beim "Verkleinern"
        #     von 139 MB auf 349 MB WUCHS, weil bereits JPEG2000-kodierte
        #     Fotoseiten blind zu JPEG umkodiert wurden. Als eigener Knopf
        #     statt automatisch bei jeder Auswahlaenderung, da die Analyse
        #     bei sehr vielen Seiten selbst spuerbar dauern kann.
        # EN: Analysis BEFORE the actual (for many pages, lengthy) export --
        #     checks how many pages are already stored in a format (JBIG2/
        #     CCITT/JPX) where JPEG re-encoding mostly doesn't make sense
        #     (see core/komprimierung.py's _bereits_effizient_komprimiert()).
        #     Exactly the case that once caused a 912-page file to GROW
        #     from 139 MB to 349 MB when "shrunk", because already-JPEG2000-
        #     encoded photo pages were blindly re-encoded as JPEG. A
        #     separate button rather than automatic on every selection
        #     change, since the analysis itself can take a noticeable while
        #     for very many pages.
        self._btn_analysieren = QPushButton(self.tr("Datei analysieren"))
        self._btn_analysieren.clicked.connect(self._analysieren)
        self._analyse_info = QLabel()
        self._analyse_info.setWordWrap(True)
        self._analyse_info.setStyleSheet("color: gray;")

        self._btn_export = QPushButton(self.tr("Als kleinere PDF exportieren …"))
        self._btn_export.clicked.connect(self._exportieren)
        self._btn_export.setEnabled(self.liste.count() > 0)
        self.liste.geaendert.connect(
            lambda: self._btn_export.setEnabled(self.liste.count() > 0)
        )

        # DE: Stapel-Variante -- verarbeitet mehrere, komplett eigenstaendige
        #     Dateien EINZELN (jede bleibt ihr eigenes Dokument), anders als
        #     der Knopf oben, der die gemeinsame Dateiliste als EINE Datei
        #     exportiert. Nutzt dieselben Qualitaets-/Aufloesungs-Felder.
        # EN: Batch variant -- processes several, completely independent
        #     files INDIVIDUALLY (each stays its own document), unlike the
        #     button above, which exports the shared page list as ONE file.
        #     Uses the same quality/resolution fields.
        btn_stapel_export = QPushButton(self.tr("Mehrere Dateien einzeln verkleinern …"))
        btn_stapel_export.clicked.connect(self._mehrere_verkleinern)

        groesse_gruppe = QGroupBox(self.tr("Dateigröße verringern"))
        groesse_layout = QVBoxLayout(groesse_gruppe)
        groesse_layout.addWidget(hinweis)
        groesse_layout.addLayout(einstellungen_zeile)
        groesse_layout.addWidget(self._pdfa_beim_export_feld)
        groesse_layout.addWidget(self._btn_analysieren)
        groesse_layout.addWidget(self._analyse_info)
        groesse_layout.addWidget(self._btn_export)
        groesse_layout.addWidget(btn_stapel_export)

        # -- PDF/A eigenstaendig / PDF/A standalone ------------------------
        pdfa_hinweis = QLabel(
            self.tr("Versieht eine beliebige, bereits vorhandene PDF-Datei nachträglich "
                   "mit den üblichen Kennzeichen für das Archivformat PDF/A-2b "
                   "(eingebettetes sRGB-Farbprofil + passende Metadaten). Diese "
                   "Kennzeichen werden von Software verlässlich erkannt, sind aber "
                   "keine förmliche Zertifizierung -- für eine verbindliche Prüfung "
                   "z. B. mit dem kostenlosen Prüfwerkzeug veraPDF gegenchecken.")
        )
        pdfa_hinweis.setWordWrap(True)
        btn_pdfa = QPushButton(self.tr("Bestehende PDF-Datei als PDF/A-2b kennzeichnen …"))
        btn_pdfa.clicked.connect(self._pdfa_eigenstaendig)
        btn_pdfa_stapel = QPushButton(self.tr("Mehrere Dateien einzeln als PDF/A-2b kennzeichnen …"))
        btn_pdfa_stapel.clicked.connect(self._mehrere_pdfa_kennzeichnen)

        pdfa_gruppe = QGroupBox(self.tr("PDF/A kennzeichnen"))
        pdfa_layout = QVBoxLayout(pdfa_gruppe)
        pdfa_layout.addWidget(pdfa_hinweis)
        pdfa_layout.addWidget(btn_pdfa)
        pdfa_layout.addWidget(btn_pdfa_stapel)

        # -- Struktur-Kompression eigenstaendig / structural compression standalone --
        struktur_hinweis = QLabel(
            self.tr("Verkleinert eine beliebige, bereits vorhandene PDF-Datei verlustfrei "
                   "-- entfernt nicht mehr benutzte bzw. doppelte Objekte und komprimiert "
                   "unkomprimierte Datenströme, ohne Bilder neu zu kodieren oder an der "
                   "Darstellung etwas zu ändern. Meist nur wenige Prozent, aber ohne "
                   "jeden Qualitätsverlust.")
        )
        struktur_hinweis.setWordWrap(True)
        btn_struktur = QPushButton(self.tr("Bestehende PDF-Datei verlustfrei komprimieren …"))
        btn_struktur.clicked.connect(self._struktur_komprimieren)
        btn_struktur_stapel = QPushButton(self.tr("Mehrere Dateien einzeln verlustfrei komprimieren …"))
        btn_struktur_stapel.clicked.connect(self._mehrere_struktur_komprimieren)

        struktur_gruppe = QGroupBox(self.tr("PDF-Struktur komprimieren (verlustfrei)"))
        struktur_layout = QVBoxLayout(struktur_gruppe)
        struktur_layout.addWidget(struktur_hinweis)
        struktur_layout.addWidget(btn_struktur)
        struktur_layout.addWidget(btn_struktur_stapel)

        layout = QVBoxLayout(self)
        layout.addWidget(groesse_gruppe)
        layout.addWidget(pdfa_gruppe)
        layout.addWidget(struktur_gruppe)
        layout.addStretch(1)

    # -- Dateigroesse verringern / reduce file size -----------------------

    def _analysieren(self) -> None:
        seiten = self.liste.seiten()
        if not seiten:
            QMessageBox.information(
                self, self.tr("Keine Seiten"), self.tr("Die Dateiliste ist leer.")
            )
            return
        try:
            effizient, gesamt = im_hintergrund_ausfuehren(
                self, self.tr("Datei wird analysiert …"),
                lambda _fortschritt: codec_analyse(seiten),
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.warning(self, self.tr("Analyse fehlgeschlagen"), str(exc))
            return

        if effizient == 0:
            self._analyse_info.setText(
                self.tr("Keine der {0} Seite(n) ist bereits effizient komprimiert -- "
                       "die JPEG-Neukodierung sollte die Datei hier tatsächlich "
                       "spürbar verkleinern.").format(gesamt)
            )
        elif effizient == gesamt:
            self._analyse_info.setText(
                self.tr("Alle {0} Seite(n) sind bereits effizient komprimiert (JBIG2/"
                       "JPEG2000) und werden unverändert übernommen -- eine weitere "
                       "Verkleinerung wird hier vermutlich wenig oder gar nichts "
                       "bringen (kann die Datei sogar vergrößern).").format(gesamt)
            )
        else:
            anteil = effizient / gesamt * 100
            self._analyse_info.setText(
                self.tr("{0} von {1} Seite(n) ({2:.0f} %) sind bereits effizient "
                       "komprimiert (JBIG2/JPEG2000) und werden unverändert "
                       "übernommen. Bei den übrigen {3} Seite(n) sollte die "
                       "JPEG-Neukodierung tatsächlich verkleinern.").format(
                    effizient, gesamt, anteil, gesamt - effizient
                )
            )

    def _exportieren(self) -> None:
        vorschlag = self.liste.dateiname_vorschlag() or self.tr("verkleinert.pdf")
        ziel_pfad = speichern_dialog(self, self.tr("PDF speichern unter"), vorschlag, self.tr("PDF-Datei (*.pdf)"))
        if ziel_pfad is None:
            return
        max_dpi = self._dpi_feld.value() if self._dpi_aktiv_feld.isChecked() else None

        seiten = self.liste.seiten()
        ausgangsgroesse = ausgangsgroesse_falls_eindeutig(seiten)
        anzeige = Fortschrittsanzeige(self, self.tr("PDF wird komprimiert …"), len(seiten))
        try:
            anzahl, groesse = export_pdf_komprimiert(
                seiten, ziel_pfad, jpeg_qualitaet=self._qualitaet_feld.value(),
                max_dpi=max_dpi, fortschritt=anzeige.callback,
                dokument_metadaten=self.liste.pdf_metadaten_felder(),
            )
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Export fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()

        if self._pdfa_beim_export_feld.isChecked():
            titel = self.liste.dokument_metadaten["titel"] or ziel_pfad.stem
            try:
                im_hintergrund_ausfuehren(
                    self, self.tr("PDF/A-Kennzeichnung wird erstellt …"),
                    lambda _f: als_pdfa_markieren(ziel_pfad, ziel_pfad, titel=titel),
                )
                groesse = ziel_pfad.stat().st_size
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(
                    self, self.tr("PDF/A-Kennzeichnung fehlgeschlagen"),
                    self.tr("Die PDF wurde exportiert, aber die PDF/A-Kennzeichnung ist "
                           "fehlgeschlagen:\n{0}").format(exc),
                )

        text = self.tr("{0} Seiten gespeichert unter:\n{1}\n\nGröße: {2}").format(
            anzahl, ziel_pfad, _lesbare_groesse(groesse)
        )
        if ausgangsgroesse is not None:
            text += self.tr(" (Original: {0})").format(_lesbare_groesse(ausgangsgroesse))
        if ausgangsgroesse is not None and groesse >= ausgangsgroesse:
            text += self.tr(
                "\n\nHinweis: Die neue Datei ist nicht kleiner als das Original. "
                "Das kann passieren, wenn die Quelle bereits effizient komprimiert ist "
                "(z. B. JPEG2000-Scans) -- JPEG ist nicht immer der sparsamere Codec. "
                "Versuchen Sie eine niedrigere JPEG-Qualität oder eine geringere "
                "Höchstauflösung."
            )
        QMessageBox.information(self, self.tr("Fertig"), text)
        self.liste.alsExportiertMarkiert.emit(ziel_pfad)

    # -- PDF/A eigenstaendig / PDF/A standalone ----------------------------

    def _pdfa_eigenstaendig(self) -> None:
        quelle_pfad = einzeln_oeffnen_dialog(self, self.tr("PDF-Datei wählen"), self.tr("PDF-Datei (*.pdf)"))
        if quelle_pfad is None:
            return
        ziel_pfad = speichern_dialog(
            self, self.tr("PDF/A speichern unter"), quelle_pfad.stem + "_pdfa.pdf", self.tr("PDF-Datei (*.pdf)")
        )
        if ziel_pfad is None:
            return
        try:
            im_hintergrund_ausfuehren(
                self, self.tr("PDF/A-Kennzeichnung wird erstellt …"),
                lambda _f: als_pdfa_markieren(quelle_pfad, ziel_pfad, titel=quelle_pfad.stem),
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Fehlgeschlagen"), str(exc))
            return
        QMessageBox.information(self, self.tr("Fertig"), self.tr("PDF/A-2b-Kennzeichnung gespeichert unter:\n{0}").format(ziel_pfad))

    # -- Struktur-Kompression eigenstaendig / structural compression standalone --

    def _struktur_komprimieren(self) -> None:
        quelle_pfad = einzeln_oeffnen_dialog(self, self.tr("PDF-Datei wählen"), self.tr("PDF-Datei (*.pdf)"))
        if quelle_pfad is None:
            return
        ziel_pfad = speichern_dialog(
            self, self.tr("Komprimierte PDF speichern unter"), quelle_pfad.stem + "_komprimiert.pdf",
            self.tr("PDF-Datei (*.pdf)"),
        )
        if ziel_pfad is None:
            return
        try:
            vorher, nachher = im_hintergrund_ausfuehren(
                self, self.tr("PDF wird komprimiert …"),
                lambda _f: strukturell_komprimieren(quelle_pfad, ziel_pfad),
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Fehlgeschlagen"), str(exc))
            return
        ersparnis = (1 - nachher / vorher) * 100 if vorher else 0
        QMessageBox.information(
            self, self.tr("Fertig"),
            self.tr("Gespeichert unter:\n{0}\n\n{1} → {2} ({3} % kleiner)").format(
                ziel_pfad, _lesbare_groesse(vorher), _lesbare_groesse(nachher), f"{ersparnis:.0f}"
            ),
        )

    # -- Stapelverarbeitung (mehrere eigenstaendige Dateien) / batch (several independent files) --

    def _stapel_verarbeiten(
        self, suffix_vorschlag: str, verarbeite: Callable[[Path, Path], None],
    ) -> None:
        """
        DE: Gemeinsamer Ablauf fuer alle drei "Mehrere Dateien …"-Knoepfe:
            Dateien waehlen, Ziel-Ordner/Namenszusatz festlegen
            (batch_ziel_dialog), dann jede Datei EINZELN mit `verarbeite`
            im Hintergrund verarbeiten -- ein Fehler bei einer Datei bricht
            die uebrigen nicht ab, sondern wird am Ende gesammelt
            aufgelistet, damit ein einzelnes Problem (z. B. eine
            beschaedigte PDF) nicht den ganzen Stapel verhindert.
        EN: Shared flow for all three "Multiple files …" buttons: choose
            files, decide target folder/name suffix (batch_ziel_dialog),
            then process each file INDIVIDUALLY with `verarbeite` in the
            background -- a failure on one file doesn't abort the rest,
            it's collected and listed at the end instead, so a single
            problem (e.g. a corrupted PDF) doesn't block the whole batch.
        """
        pfade = oeffnen_dialog(self, self.tr("Dateien wählen"), self.tr("PDF-Datei (*.pdf)"))
        if not pfade:
            return
        wahl = batch_ziel_dialog(self, suffix_vorschlag)
        if wahl is None:
            return

        def ziel_fuer(quelle: Path) -> Path:
            ordner = wahl.ordner or quelle.parent
            return ordner / f"{quelle.stem}{wahl.suffix}{quelle.suffix}"

        ziele = [ziel_fuer(p) for p in pfade]
        if len(set(ziele)) != len(ziele):
            antwort = QMessageBox.warning(
                self, self.tr("Mehrdeutiges Ziel"),
                self.tr("Mehrere Ausgabedateien hätten denselben Namen im selben Ordner und "
                       "würden sich gegenseitig überschreiben. Trotzdem fortfahren?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if antwort != QMessageBox.StandardButton.Yes:
                return

        def _lauf(fortschritt):
            erfolge = 0
            fehler: list[tuple[Path, str]] = []
            vorher_gesamt = 0
            nachher_gesamt = 0
            for i, (quelle, ziel) in enumerate(zip(pfade, ziele), start=1):
                try:
                    vorher_gesamt += quelle.stat().st_size
                    verarbeite(quelle, ziel)
                    nachher_gesamt += ziel.stat().st_size
                    erfolge += 1
                except Exception as exc:  # noqa: BLE001 -- pro Datei sammeln statt abzubrechen
                    fehler.append((quelle, str(exc)))
                fortschritt(i, len(pfade))
            return erfolge, fehler, vorher_gesamt, nachher_gesamt

        try:
            erfolge, fehler, vorher_gesamt, nachher_gesamt = im_hintergrund_ausfuehren(
                self, self.tr("Dateien werden verarbeitet …"), _lauf,
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Fehlgeschlagen"), str(exc))
            return

        text = self.tr("{0} von {1} Datei(en) erfolgreich verarbeitet.").format(erfolge, len(pfade))
        if vorher_gesamt:
            text += "\n\n" + self.tr("{0} → {1} insgesamt").format(
                _lesbare_groesse(vorher_gesamt), _lesbare_groesse(nachher_gesamt)
            )
        if fehler:
            text += "\n\n" + self.tr("Fehler bei:") + "\n" + "\n".join(
                f"{quelle.name}: {meldung}" for quelle, meldung in fehler
            )
            QMessageBox.warning(self, self.tr("Fertig mit Fehlern"), text)
        else:
            QMessageBox.information(self, self.tr("Fertig"), text)

    def _mehrere_verkleinern(self) -> None:
        qualitaet = self._qualitaet_feld.value()
        max_dpi = self._dpi_feld.value() if self._dpi_aktiv_feld.isChecked() else None

        def verarbeite(quelle: Path, ziel: Path) -> None:
            seiten = [WorkingPage(source=quelle_seite) for quelle_seite in datei_aufschluesseln(quelle)]
            export_pdf_komprimiert(seiten, ziel, jpeg_qualitaet=qualitaet, max_dpi=max_dpi)

        self._stapel_verarbeiten("_verkleinert", verarbeite)

    def _mehrere_pdfa_kennzeichnen(self) -> None:
        def verarbeite(quelle: Path, ziel: Path) -> None:
            als_pdfa_markieren(quelle, ziel, titel=quelle.stem)

        self._stapel_verarbeiten("_pdfa", verarbeite)

    def _mehrere_struktur_komprimieren(self) -> None:
        def verarbeite(quelle: Path, ziel: Path) -> None:
            strukturell_komprimieren(quelle, ziel)

        self._stapel_verarbeiten("_komprimiert", verarbeite)
