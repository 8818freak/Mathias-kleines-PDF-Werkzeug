"""
DE: Werkzeug "PDF in Bilder teilen": exportiert die gemeinsame Seitenliste
    als Bilddateien -- entweder als einzelne, durchnummerierte Dateien
    (PDF/JPEG/TIFF/BMP, eine je Seite bzw. Teilstueck) oder als EINE
    mehrseitige TIFF-Datei. Die Seiten selbst kommen wie bei jedem anderen
    Werkzeug aus dem gemeinsamen Datei-Panel, inklusive bereits
    vorgenommener Drehungen, Spiegelungen und Teilungen.

EN: "Split PDF into images" tool: exports the shared page list as image
    files -- either as individual, sequentially numbered files
    (PDF/JPEG/TIFF/BMP, one per page or split part) or as ONE multi-page
    TIFF file. The pages themselves come from the shared file panel like
    with every other tool, including any rotation, mirroring, and
    splitting already applied.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from pdfkrams.core.export_dateien import export_einzeldateien, export_mehrseitige_tiff
from pdfkrams.gui.widgets.export_dialog import einzelexport_abfragen
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget


class PdfZuBildernToolWidget(QWidget):
    """
    DE: GUI-Seite fuer den Export der gemeinsamen Seitenliste als Bilddateien.
    EN: GUI page for exporting the shared page list as image files.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        hinweis = QLabel(
            "Exportiert die Dateiliste links (inklusive bereits vorgenommener "
            "Drehungen, Spiegelungen und Teilungen) als Bilder -- entweder als "
            "einzelne durchnummerierte Dateien oder als eine mehrseitige "
            "TIFF-Datei."
        )
        hinweis.setWordWrap(True)

        self._btn_einzeln = QPushButton("Als einzelne nummerierte Dateien exportieren …")
        self._btn_einzeln.setToolTip(
            "PDF, JPEG, TIFF oder BMP -- eine Datei je Seite bzw. Teilstück, "
            "z. B. 0001.jpg, 0002.jpg, …"
        )
        self._btn_einzeln.clicked.connect(self._als_einzeldateien_exportieren)

        self._btn_mehrseitig = QPushButton("Als eine mehrseitige TIFF-Datei exportieren …")
        self._btn_mehrseitig.clicked.connect(self._als_mehrseitige_tiff_exportieren)

        self._aktivierung_aktualisieren()
        self.liste.geaendert.connect(self._aktivierung_aktualisieren)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addStretch(1)
        layout.addWidget(self._btn_einzeln)
        layout.addWidget(self._btn_mehrseitig)

    def _aktivierung_aktualisieren(self) -> None:
        an = self.liste.count() > 0
        self._btn_einzeln.setEnabled(an)
        self._btn_mehrseitig.setEnabled(an)

    def _als_einzeldateien_exportieren(self) -> None:
        einstellungen = einzelexport_abfragen(self)
        if einstellungen is None:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, "Dateien werden geschrieben …", len(seiten))
        try:
            pfade = export_einzeldateien(
                seiten, einstellungen.zielordner, einstellungen.endung,
                basis=einstellungen.basis, start=einstellungen.start, stellen=einstellungen.stellen,
                fortschritt=anzeige.callback,
            )
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, "Export fehlgeschlagen", str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(
            self, "Fertig", f"{len(pfade)} Dateien gespeichert in:\n{einstellungen.zielordner}"
        )

    def _als_mehrseitige_tiff_exportieren(self) -> None:
        ziel, _ = QFileDialog.getSaveFileName(
            self, "TIFF speichern unter", "seiten.tif", "TIFF-Datei (*.tif *.tiff)"
        )
        if not ziel:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, "TIFF wird erstellt …", len(seiten))
        try:
            anzahl = export_mehrseitige_tiff(seiten, Path(ziel), fortschritt=anzeige.callback)
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, "Export fehlgeschlagen", str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(self, "Fertig", f"{anzahl} Seiten gespeichert in:\n{ziel}")
