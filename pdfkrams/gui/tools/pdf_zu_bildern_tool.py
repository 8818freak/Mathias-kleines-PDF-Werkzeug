"""
DE: Werkzeug "PDF in Bilder teilen": exportiert die gemeinsame Seitenliste
    als Bilddateien -- entweder als einzelne, durchnummerierte Dateien
    (PDF/JPEG/TIFF/BMP, eine je Seite bzw. Teilstueck) oder als EINE
    mehrseitige TIFF-Datei. Die Seiten selbst kommen wie bei jedem anderen
    Werkzeug aus dem gemeinsamen Datei-Panel, inklusive bereits
    vorgenommener Drehungen, Spiegelungen und Teilungen. Zusaetzlich lassen
    sich hier -- wie im Werkzeug "PDF erstellen" -- nur die markierten
    Seiten als eigene, neue (weiterhin mehrseitige) PDF-Datei entnehmen,
    statt in Einzelseiten zerlegt zu werden.

EN: "Split PDF into images" tool: exports the shared page list as image
    files -- either as individual, sequentially numbered files
    (PDF/JPEG/TIFF/BMP, one per page or split part) or as ONE multi-page
    TIFF file. The pages themselves come from the shared file panel like
    with every other tool, including any rotation, mirroring, and
    splitting already applied. Additionally -- like in the "Create PDF"
    tool -- just the marked pages can be taken out here as their own new
    (still multi-page) PDF file, instead of being broken up into single
    pages.
"""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from pdfkrams.core.export_dateien import export_einzeldateien, export_mehrseitige_tiff
from pdfkrams.gui.widgets.datei_dialoge import speichern_dialog
from pdfkrams.gui.widgets.export_dialog import einzelexport_abfragen
from pdfkrams.gui.widgets.fortschritt import Abgebrochen, Fortschrittsanzeige
from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.pdf_export import ausgewaehlte_als_pdf_exportieren


class PdfZuBildernToolWidget(QWidget):
    """
    DE: GUI-Seite fuer den Export der gemeinsamen Seitenliste als Bilddateien.
    EN: GUI page for exporting the shared page list as image files.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        hinweis = QLabel(
            self.tr("Exportiert die Dateiliste links (inklusive bereits vorgenommener "
                   "Drehungen, Spiegelungen und Teilungen) als Bilder -- entweder als "
                   "einzelne durchnummerierte Dateien oder als eine mehrseitige "
                   "TIFF-Datei.")
        )
        hinweis.setWordWrap(True)

        self._btn_einzeln = QPushButton(self.tr("Als einzelne nummerierte Dateien exportieren …"))
        self._btn_einzeln.setToolTip(
            self.tr("PDF, JPEG, TIFF oder BMP -- eine Datei je Seite bzw. Teilstück, "
                   "z. B. 0001.jpg, 0002.jpg, …")
        )
        self._btn_einzeln.clicked.connect(self._als_einzeldateien_exportieren)

        self._btn_mehrseitig = QPushButton(self.tr("Als eine mehrseitige TIFF-Datei exportieren …"))
        self._btn_mehrseitig.clicked.connect(self._als_mehrseitige_tiff_exportieren)

        self._aktivierung_aktualisieren()
        self.liste.geaendert.connect(self._aktivierung_aktualisieren)

        # DE: Siehe CombineToolWidget -- dieselbe "Seiten entnehmen"-Gruppe,
        #     hier zusaetzlich angeboten, da naheliegend, sie auch in einem
        #     Werkzeug zu suchen, das "PDF ... zerteilen" heisst.
        # EN: See CombineToolWidget -- the same "Take out pages" group,
        #     also offered here, since it's natural to look for it in a
        #     tool named "Split PDF ...", too.
        auswahl_hinweis = QLabel(
            self.tr("Nur die markierten Seiten als eigene, neue PDF-Datei entnehmen "
                   "(bleibt mehrseitig, wird NICHT in Einzelseiten zerlegt):")
        )
        auswahl_hinweis.setWordWrap(True)
        btn_auswahl_kopieren = QPushButton(self.tr("Markierte Seiten als neue Datei exportieren …"))
        btn_auswahl_kopieren.clicked.connect(lambda: self._auswahl_exportieren(entfernen=False))
        btn_auswahl_verschieben = QPushButton(self.tr("Markierte Seiten in neue Datei verschieben …"))
        btn_auswahl_verschieben.setToolTip(
            self.tr("Wie „… exportieren“, entfernt die markierten Seiten danach zusätzlich aus "
                   "der aktuellen Liste.")
        )
        btn_auswahl_verschieben.clicked.connect(lambda: self._auswahl_exportieren(entfernen=True))

        auswahl_gruppe = QGroupBox(self.tr("Seiten entnehmen"))
        auswahl_layout = QVBoxLayout(auswahl_gruppe)
        auswahl_layout.addWidget(auswahl_hinweis)
        auswahl_layout.addWidget(btn_auswahl_kopieren)
        auswahl_layout.addWidget(btn_auswahl_verschieben)

        layout = QVBoxLayout(self)
        layout.addWidget(hinweis)
        layout.addWidget(self._btn_einzeln)
        layout.addWidget(self._btn_mehrseitig)
        layout.addStretch(1)
        layout.addWidget(auswahl_gruppe)

    def _aktivierung_aktualisieren(self) -> None:
        an = self.liste.count() > 0
        self._btn_einzeln.setEnabled(an)
        self._btn_mehrseitig.setEnabled(an)

    def _als_einzeldateien_exportieren(self) -> None:
        einstellungen = einzelexport_abfragen(self)
        if einstellungen is None:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, self.tr("Dateien werden geschrieben …"), len(seiten))
        try:
            pfade = export_einzeldateien(
                seiten, einstellungen.zielordner, einstellungen.endung,
                basis=einstellungen.basis, start=einstellungen.start, stellen=einstellungen.stellen,
                fortschritt=anzeige.callback,
            )
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Export fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(
            self, self.tr("Fertig"), self.tr("{0} Dateien gespeichert in:\n{1}").format(len(pfade), einstellungen.zielordner)
        )

    def _als_mehrseitige_tiff_exportieren(self) -> None:
        ziel = speichern_dialog(
            self, self.tr("TIFF speichern unter"), self.tr("seiten.tif"), self.tr("TIFF-Datei (*.tif *.tiff)")
        )
        if ziel is None:
            return
        seiten = self.liste.seiten()
        anzeige = Fortschrittsanzeige(self, self.tr("TIFF wird erstellt …"), len(seiten))
        try:
            anzahl = export_mehrseitige_tiff(seiten, ziel, fortschritt=anzeige.callback)
        except Abgebrochen:
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Export fehlgeschlagen"), str(exc))
            return
        finally:
            anzeige.schliessen()
        QMessageBox.information(self, self.tr("Fertig"), self.tr("{0} Seiten gespeichert in:\n{1}").format(anzahl, ziel))

    def _auswahl_exportieren(self, entfernen: bool) -> None:
        ausgewaehlte_als_pdf_exportieren(
            self, self.liste, entfernen=entfernen,
            dialog_titel=self.tr("PDF speichern unter"),
            dateiname_vorschlag=self.tr("auszug.pdf"),
            dialog_filter=self.tr("PDF-Datei (*.pdf)"),
            fortschritt_text=self.tr("PDF wird erstellt …"),
            fehler_titel=self.tr("Export fehlgeschlagen"),
            erfolg_titel=self.tr("Fertig"),
            erfolg_text_vorlage=self.tr("PDF gespeichert unter:\n{0}"),
            keine_auswahl_titel=self.tr("Keine Auswahl"),
            keine_auswahl_text=self.tr("Bitte zuerst Seiten in der Liste links auswählen."),
        )
