"""
DE: Werkzeug "PDF verkleinern & PDF/A": exportiert die gemeinsame
    Seitenliste als deutlich kleinere PDF-Datei (JPEG-Kodierung statt
    verlustfrei, wählbare Qualität und Höchstauflösung -- bei gescannten
    Dokumenten typischerweise um ein Vielfaches kleiner) und kann jede
    PDF-Datei nachträglich mit den strukturellen Kennzeichen fürs
    Archivformat PDF/A-2b versehen (eingebettetes Farbprofil + passende
    Metadaten).

EN: "Shrink PDF & PDF/A" tool: exports the shared page list as a
    significantly smaller PDF file (JPEG encoding instead of lossless,
    selectable quality and maximum resolution -- for scanned documents
    typically many times smaller) and can retrofit any PDF file with the
    structural markers for the PDF/A-2b archival format (embedded color
    profile + matching metadata).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.komprimierung import (
    ausgangsgroesse_falls_eindeutig,
    export_pdf_komprimiert,
    strukturell_komprimieren,
)
from pdfkrams.core.pdfa import als_pdfa_markieren
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
            "Exportiert die Dateiliste links als deutlich kleinere PDF-Datei -- "
            "jede Seite wird verlustbehaftet als JPEG statt verlustfrei "
            "kodiert. Bei gescannten Dokumenten oft 10-100x kleiner. Nicht "
            "geeignet für Seiten mit echtem Vektortext (der wird dabei zu "
            "Pixeln)."
        )
        hinweis.setWordWrap(True)

        einstellungen_zeile = QHBoxLayout()
        self._qualitaet_feld = QSpinBox()
        self._qualitaet_feld.setRange(1, 95)
        self._qualitaet_feld.setValue(75)
        self._qualitaet_feld.setPrefix("JPEG-Qualität: ")
        self._qualitaet_feld.setSuffix(" %")

        self._dpi_aktiv_feld = QCheckBox("Auflösung begrenzen auf")
        self._dpi_aktiv_feld.setChecked(True)
        self._dpi_feld = QSpinBox()
        self._dpi_feld.setRange(50, 1200)
        self._dpi_feld.setValue(200)
        self._dpi_feld.setSuffix(" dpi")
        self._dpi_aktiv_feld.toggled.connect(self._dpi_feld.setEnabled)

        einstellungen_zeile.addWidget(self._qualitaet_feld)
        einstellungen_zeile.addWidget(self._dpi_aktiv_feld)
        einstellungen_zeile.addWidget(self._dpi_feld)

        self._pdfa_beim_export_feld = QCheckBox("Zusätzlich als PDF/A-2b kennzeichnen")

        self._btn_export = QPushButton("Als kleinere PDF exportieren …")
        self._btn_export.clicked.connect(self._exportieren)
        self._btn_export.setEnabled(self.liste.count() > 0)
        self.liste.geaendert.connect(
            lambda: self._btn_export.setEnabled(self.liste.count() > 0)
        )

        groesse_gruppe = QGroupBox("Dateigröße verringern")
        groesse_layout = QVBoxLayout(groesse_gruppe)
        groesse_layout.addWidget(hinweis)
        groesse_layout.addLayout(einstellungen_zeile)
        groesse_layout.addWidget(self._pdfa_beim_export_feld)
        groesse_layout.addWidget(self._btn_export)

        # -- PDF/A eigenstaendig / PDF/A standalone ------------------------
        pdfa_hinweis = QLabel(
            "Versieht eine beliebige, bereits vorhandene PDF-Datei nachträglich "
            "mit den üblichen Kennzeichen für das Archivformat PDF/A-2b "
            "(eingebettetes sRGB-Farbprofil + passende Metadaten). Diese "
            "Kennzeichen werden von Software verlässlich erkannt, sind aber "
            "keine förmliche Zertifizierung -- für eine verbindliche Prüfung "
            "z. B. mit dem kostenlosen Prüfwerkzeug veraPDF gegenchecken."
        )
        pdfa_hinweis.setWordWrap(True)
        btn_pdfa = QPushButton("Bestehende PDF-Datei als PDF/A-2b kennzeichnen …")
        btn_pdfa.clicked.connect(self._pdfa_eigenstaendig)

        pdfa_gruppe = QGroupBox("PDF/A kennzeichnen")
        pdfa_layout = QVBoxLayout(pdfa_gruppe)
        pdfa_layout.addWidget(pdfa_hinweis)
        pdfa_layout.addWidget(btn_pdfa)

        # -- Struktur-Kompression eigenstaendig / structural compression standalone --
        struktur_hinweis = QLabel(
            "Verkleinert eine beliebige, bereits vorhandene PDF-Datei verlustfrei "
            "-- entfernt nicht mehr benutzte bzw. doppelte Objekte und komprimiert "
            "unkomprimierte Datenströme, ohne Bilder neu zu kodieren oder an der "
            "Darstellung etwas zu ändern. Meist nur wenige Prozent, aber ohne "
            "jeden Qualitätsverlust."
        )
        struktur_hinweis.setWordWrap(True)
        btn_struktur = QPushButton("Bestehende PDF-Datei verlustfrei komprimieren …")
        btn_struktur.clicked.connect(self._struktur_komprimieren)

        struktur_gruppe = QGroupBox("PDF-Struktur komprimieren (verlustfrei)")
        struktur_layout = QVBoxLayout(struktur_gruppe)
        struktur_layout.addWidget(struktur_hinweis)
        struktur_layout.addWidget(btn_struktur)

        layout = QVBoxLayout(self)
        layout.addWidget(groesse_gruppe)
        layout.addWidget(pdfa_gruppe)
        layout.addWidget(struktur_gruppe)
        layout.addStretch(1)

    # -- Dateigroesse verringern / reduce file size -----------------------

    def _exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, "PDF speichern unter", "verkleinert.pdf", "PDF-Datei (*.pdf)"
        )
        if not ziel:
            return
        ziel_pfad = Path(ziel)
        max_dpi = self._dpi_feld.value() if self._dpi_aktiv_feld.isChecked() else None

        seiten = self.liste.seiten()
        ausgangsgroesse = ausgangsgroesse_falls_eindeutig(seiten)
        anzeige = Fortschrittsanzeige(self, "PDF wird komprimiert …", len(seiten))
        try:
            anzahl, groesse = export_pdf_komprimiert(
                seiten, ziel_pfad, jpeg_qualitaet=self._qualitaet_feld.value(),
                max_dpi=max_dpi, fortschritt=anzeige.callback,
            )
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, "Export fehlgeschlagen", str(exc))
            return
        finally:
            anzeige.schliessen()

        if self._pdfa_beim_export_feld.isChecked():
            try:
                im_hintergrund_ausfuehren(
                    self, "PDF/A-Kennzeichnung wird erstellt …",
                    lambda _f: als_pdfa_markieren(ziel_pfad, ziel_pfad, titel=ziel_pfad.stem),
                )
                groesse = ziel_pfad.stat().st_size
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(
                    self, "PDF/A-Kennzeichnung fehlgeschlagen",
                    f"Die PDF wurde exportiert, aber die PDF/A-Kennzeichnung ist "
                    f"fehlgeschlagen:\n{exc}",
                )

        text = f"{anzahl} Seiten gespeichert unter:\n{ziel_pfad}\n\nGröße: {_lesbare_groesse(groesse)}"
        if ausgangsgroesse is not None:
            text += f" (Original: {_lesbare_groesse(ausgangsgroesse)})"
        if ausgangsgroesse is not None and groesse >= ausgangsgroesse:
            text += (
                "\n\nHinweis: Die neue Datei ist nicht kleiner als das Original. "
                "Das kann passieren, wenn die Quelle bereits effizient komprimiert ist "
                "(z. B. JPEG2000-Scans) -- JPEG ist nicht immer der sparsamere Codec. "
                "Versuchen Sie eine niedrigere JPEG-Qualität oder eine geringere "
                "Höchstauflösung."
            )
        QMessageBox.information(self, "Fertig", text)

    # -- PDF/A eigenstaendig / PDF/A standalone ----------------------------

    def _pdfa_eigenstaendig(self) -> None:
        quelle, _ = QFileDialog.getOpenFileName(self, "PDF-Datei wählen", "", "PDF-Datei (*.pdf)")
        if not quelle:
            return
        ziel, _ = QFileDialog.getSaveFileName(
            self, "PDF/A speichern unter", Path(quelle).stem + "_pdfa.pdf", "PDF-Datei (*.pdf)"
        )
        if not ziel:
            return
        quelle_pfad, ziel_pfad = Path(quelle), Path(ziel)
        try:
            im_hintergrund_ausfuehren(
                self, "PDF/A-Kennzeichnung wird erstellt …",
                lambda _f: als_pdfa_markieren(quelle_pfad, ziel_pfad, titel=quelle_pfad.stem),
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, "Fehlgeschlagen", str(exc))
            return
        QMessageBox.information(self, "Fertig", f"PDF/A-2b-Kennzeichnung gespeichert unter:\n{ziel}")

    # -- Struktur-Kompression eigenstaendig / structural compression standalone --

    def _struktur_komprimieren(self) -> None:
        quelle, _ = QFileDialog.getOpenFileName(self, "PDF-Datei wählen", "", "PDF-Datei (*.pdf)")
        if not quelle:
            return
        ziel, _ = QFileDialog.getSaveFileName(
            self, "Komprimierte PDF speichern unter", Path(quelle).stem + "_komprimiert.pdf",
            "PDF-Datei (*.pdf)",
        )
        if not ziel:
            return
        quelle_pfad, ziel_pfad = Path(quelle), Path(ziel)
        try:
            vorher, nachher = im_hintergrund_ausfuehren(
                self, "PDF wird komprimiert …",
                lambda _f: strukturell_komprimieren(quelle_pfad, ziel_pfad),
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, "Fehlgeschlagen", str(exc))
            return
        ersparnis = (1 - nachher / vorher) * 100 if vorher else 0
        QMessageBox.information(
            self, "Fertig",
            f"Gespeichert unter:\n{ziel}\n\n"
            f"{_lesbare_groesse(vorher)} → {_lesbare_groesse(nachher)} ({ersparnis:.0f} % kleiner)",
        )
