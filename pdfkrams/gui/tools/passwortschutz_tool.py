"""
DE: Werkzeug "Passwortschutz": PDF-Dateien mit einem Passwort versehen --
    einzeln, fuer einen ganzen Ordner (samt Unterordnern, alle mit
    demselben Passwort) oder anhand einer Liste aus Datei+Passwort-Paaren
    (jede Datei mit ihrem eigenen Passwort). Die drei Aktionen teilen
    sich EINE gemeinsame Einstellungsgruppe (Verfahren, Rechte-Passwort,
    Berechtigungen). Dazu ein einfaches, unverschluesseltes Log aller
    vergebenen Passwoerter (siehe core/passwort_log.py), das sich als
    CSV exportieren/importieren laesst -- eine exportierte Log-Datei ist
    direkt wieder als Eingabe fuer "Nach Liste verschluesseln" nutzbar.

    Ordner- und Listen-Verschluesselung arbeiten IN-PLACE (siehe
    core/passwortschutz.py) -- deshalb vor dem Start jeweils eine
    Rueckfrage, und Fehler bei einzelnen Dateien brechen den Rest des
    Stapels nicht ab.

EN: "Password protection" tool: add a password to PDF files -- a single
    file, an entire folder (including subfolders, all with the same
    password), or from a list of file+password pairs (each file with its
    own password). The three actions share ONE settings group (method,
    permissions password, permissions). Plus a simple, unencrypted log of
    all passwords that have been set (see core/passwort_log.py), which
    can be exported/imported as CSV -- an exported log file can directly
    be reused as input for "Encrypt from list".

    Folder and list encryption operate IN-PLACE (see
    core/passwortschutz.py) -- hence a confirmation prompt before
    starting either, and errors on individual files don't abort the
    rest of the batch.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdfkrams.core.passwort_log import LogEintrag, csv_als_log, dicts_zu_log, liste_aus_csv, log_als_csv, log_zu_dicts
from pdfkrams.core.passwortschutz import STANDARD_VERFAHREN, VERFAHREN, Schutzeinstellungen, liste_verschluesseln, ordner_verschluesseln, passwort_hinzufuegen
from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.widgets.datei_dialoge import einzeln_oeffnen_dialog, ordner_dialog, speichern_dialog
from pdfkrams.gui.widgets.hintergrund import im_hintergrund_ausfuehren
from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.passwort_feld import PasswortFeld

# DE: Anzeigename -> interner Schluessel (siehe core/passwortschutz.py's VERFAHREN).
# EN: Display name -> internal key (see core/passwortschutz.py's VERFAHREN).
_VERFAHREN_ANZEIGE: dict[str, str] = {
    "RC4, 40-Bit (alt, sehr kompatibel)": "rc4_40",
    "RC4, 128-Bit": "rc4_128",
    "AES, 128-Bit": "aes_128",
    "AES, 256-Bit (empfohlen)": "aes_256",
}

_LOG_SPALTEN = ("Datei", "Nutzerpasswort", "Eigentümerpasswort", "Verfahren", "Zeitpunkt")


class PasswortschutzToolWidget(QWidget):
    """
    DE: GUI-Seite fuer Passwortschutz (einzeln/Ordner/Liste) plus Passwort-Log.
    EN: GUI page for password protection (single/folder/list) plus password log.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        layout = QVBoxLayout(self)
        layout.addWidget(self._einstellungen_gruppe())
        layout.addWidget(self._einzeldatei_gruppe())
        layout.addWidget(self._ordner_gruppe())
        layout.addWidget(self._liste_gruppe())
        layout.addWidget(self._log_gruppe(), 1)

        self._log_tabelle_aktualisieren()

    # -- Gemeinsame Einstellungen / shared settings -------------------------

    def _einstellungen_gruppe(self) -> QGroupBox:
        self._verfahren_feld = QComboBox()
        for anzeige, schluessel in _VERFAHREN_ANZEIGE.items():
            # DE: self.tr(anzeige) statt eines literalen Strings -- siehe
            #     die Begruendung bei main_window.py's _WERKZEUGE-Schleife.
            #     Auswahl ueber currentData() (der unuebersetzte Schluessel),
            #     nicht currentText(), damit das auch bei aktiver
            #     Uebersetzung funktioniert.
            # EN: self.tr(anzeige) instead of a literal string -- see the
            #     rationale at main_window.py's _WERKZEUGE loop. Selection
            #     via currentData() (the untranslated key), not
            #     currentText(), so this keeps working with an active
            #     translation.
            self._verfahren_feld.addItem(self.tr(anzeige), schluessel)
        self._verfahren_feld.setCurrentIndex(self._verfahren_feld.findData(STANDARD_VERFAHREN))

        self._owner_feld = PasswortFeld(self.tr("wie Nutzerpasswort, falls leer"))

        self._drucken_feld = QCheckBox(self.tr("Drucken erlauben"))
        self._drucken_feld.setChecked(True)
        self._kopieren_feld = QCheckBox(self.tr("Kopieren/Extrahieren erlauben"))
        self._kopieren_feld.setChecked(True)
        self._bearbeiten_feld = QCheckBox(self.tr("Bearbeiten erlauben"))
        self._bearbeiten_feld.setChecked(True)
        berechtigungen_zeile = QHBoxLayout()
        berechtigungen_zeile.addWidget(self._drucken_feld)
        berechtigungen_zeile.addWidget(self._kopieren_feld)
        berechtigungen_zeile.addWidget(self._bearbeiten_feld)

        gruppe = QGroupBox(self.tr("Verschlüsselungseinstellungen (gelten für alle drei Aktionen unten)"))
        v = QVBoxLayout(gruppe)
        v.addWidget(QLabel(self.tr("Verfahren:")))
        v.addWidget(self._verfahren_feld)
        v.addWidget(QLabel(self.tr("Rechte-Passwort (Eigentümer -- darf trotz Einschränkungen alles):")))
        v.addWidget(self._owner_feld)
        v.addLayout(berechtigungen_zeile)
        return gruppe

    def _aktuelle_einstellungen(self) -> Schutzeinstellungen:
        return Schutzeinstellungen(
            verfahren=self._verfahren_feld.currentData(),
            owner_passwort=self._owner_feld.text(),
            drucken_erlauben=self._drucken_feld.isChecked(),
            kopieren_erlauben=self._kopieren_feld.isChecked(),
            bearbeiten_erlauben=self._bearbeiten_feld.isChecked(),
        )

    # -- Einzelne Datei / single file ----------------------------------------

    def _einzeldatei_gruppe(self) -> QGroupBox:
        hinweis = QLabel(
            self.tr("Versieht eine einzelne, bereits vorhandene PDF-Datei mit einem Passwort.")
        )
        hinweis.setWordWrap(True)
        self._einzel_passwort_feld = PasswortFeld(self.tr("Nutzerpasswort (zum Öffnen)"))
        btn = QPushButton(self.tr("Datei wählen && schützen …"))
        btn.clicked.connect(self._einzeldatei_schuetzen)

        gruppe = QGroupBox(self.tr("Einzelne Datei schützen"))
        v = QVBoxLayout(gruppe)
        v.addWidget(hinweis)
        v.addWidget(self._einzel_passwort_feld)
        v.addWidget(btn)
        return gruppe

    def _einzeldatei_schuetzen(self) -> None:
        passwort = self._einzel_passwort_feld.text()
        if not passwort:
            QMessageBox.information(self, self.tr("Passwort fehlt"), self.tr("Bitte ein Nutzerpasswort eingeben."))
            return
        quelle = einzeln_oeffnen_dialog(self, self.tr("PDF-Datei wählen"), self.tr("PDF-Datei (*.pdf)"))
        if quelle is None:
            return
        ziel = speichern_dialog(
            self, self.tr("Geschützte PDF speichern unter"), quelle.stem + "_geschuetzt.pdf",
            self.tr("PDF-Datei (*.pdf)"),
        )
        if ziel is None:
            return
        einstellungen_wert = self._aktuelle_einstellungen()
        try:
            im_hintergrund_ausfuehren(
                self, self.tr("PDF wird geschützt …"),
                lambda _f: passwort_hinzufuegen(quelle, ziel, passwort, einstellungen_wert),
            )
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Fehlgeschlagen"), str(exc))
            return
        self._log_ergaenzen([LogEintrag.jetzt(ziel, passwort, einstellungen_wert.owner_passwort, einstellungen_wert.verfahren)])
        QMessageBox.information(self, self.tr("Fertig"), self.tr("Geschützte PDF gespeichert unter:\n{0}").format(ziel))

    # -- Ordner / folder ------------------------------------------------------

    def _ordner_gruppe(self) -> QGroupBox:
        hinweis = QLabel(
            self.tr("Verschlüsselt ALLE PDF-Dateien in einem Ordner samt Unterordnern mit demselben "
                   "Passwort -- direkt in den Originaldateien (nicht als Kopie). Vorher ein Backup "
                   "anlegen, falls die Dateien noch woanders gebraucht werden.")
        )
        hinweis.setWordWrap(True)
        self._ordner_passwort_feld = PasswortFeld(self.tr("Passwort für alle Dateien in diesem Ordner"))
        btn = QPushButton(self.tr("Ordner wählen && verschlüsseln …"))
        btn.clicked.connect(self._ordner_verschluesseln)

        gruppe = QGroupBox(self.tr("Ordner verschlüsseln (inkl. Unterordner)"))
        v = QVBoxLayout(gruppe)
        v.addWidget(hinweis)
        v.addWidget(self._ordner_passwort_feld)
        v.addWidget(btn)
        return gruppe

    def _ordner_verschluesseln(self) -> None:
        passwort = self._ordner_passwort_feld.text()
        if not passwort:
            QMessageBox.information(self, self.tr("Passwort fehlt"), self.tr("Bitte ein Passwort eingeben."))
            return
        ordner = ordner_dialog(self, self.tr("Ordner wählen"))
        if ordner is None:
            return
        anzahl = len(list(ordner.rglob("*.pdf")))
        if anzahl == 0:
            QMessageBox.information(self, self.tr("Keine PDF-Dateien"), self.tr("In diesem Ordner (und Unterordnern) liegen keine PDF-Dateien."))
            return
        antwort = QMessageBox.question(
            self, self.tr("Wirklich verschlüsseln?"),
            self.tr("{0} PDF-Datei(en) in \"{1}\" (samt Unterordnern) werden DIREKT verschlüsselt, "
                   "nicht als Kopie. Fortfahren?").format(anzahl, ordner),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return
        einstellungen_wert = self._aktuelle_einstellungen()
        erfolg, fehler = im_hintergrund_ausfuehren(
            self, self.tr("Ordner wird verschlüsselt …"),
            lambda f: ordner_verschluesseln(ordner, passwort, einstellungen_wert, fortschritt=f),
        )
        self._log_ergaenzen([
            LogEintrag.jetzt(pfad, passwort, einstellungen_wert.owner_passwort, einstellungen_wert.verfahren)
            for pfad in erfolg
        ])
        self._batch_ergebnis_anzeigen(len(erfolg), fehler)

    # -- Nach Liste / from list ------------------------------------------------

    def _liste_gruppe(self) -> QGroupBox:
        hinweis = QLabel(
            self.tr("Verschlüsselt Dateien anhand einer CSV-Liste (Spalten \"Dateipfad;Passwort\", "
                   "eine exportierte Log-Datei unten passt direkt) -- jede Datei DIREKT mit ihrem "
                   "eigenen Passwort, nicht als Kopie.")
        )
        hinweis.setWordWrap(True)
        btn = QPushButton(self.tr("Listendatei wählen && verschlüsseln …"))
        btn.clicked.connect(self._liste_verschluesseln)

        gruppe = QGroupBox(self.tr("Nach Liste verschlüsseln"))
        v = QVBoxLayout(gruppe)
        v.addWidget(hinweis)
        v.addWidget(btn)
        return gruppe

    def _liste_verschluesseln(self) -> None:
        listendatei = einzeln_oeffnen_dialog(self, self.tr("Liste wählen"), self.tr("CSV-Datei (*.csv)"))
        if listendatei is None:
            return
        eintraege = liste_aus_csv(listendatei.read_text(encoding="utf-8"))
        if not eintraege:
            QMessageBox.information(self, self.tr("Leere Liste"), self.tr("In dieser Datei stehen keine gültigen Zeilen."))
            return
        antwort = QMessageBox.question(
            self, self.tr("Wirklich verschlüsseln?"),
            self.tr("{0} Datei(en) aus der Liste werden DIREKT verschlüsselt, nicht als Kopie. "
                   "Fortfahren?").format(len(eintraege)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return
        einstellungen_wert = self._aktuelle_einstellungen()
        erfolg, fehler = im_hintergrund_ausfuehren(
            self, self.tr("Dateien werden verschlüsselt …"),
            lambda f: liste_verschluesseln(eintraege, einstellungen_wert, fortschritt=f),
        )
        passwoerter = dict(eintraege)
        self._log_ergaenzen([
            LogEintrag.jetzt(pfad, passwoerter.get(pfad, ""), einstellungen_wert.owner_passwort, einstellungen_wert.verfahren)
            for pfad in erfolg
        ])
        self._batch_ergebnis_anzeigen(len(erfolg), fehler)

    def _batch_ergebnis_anzeigen(self, anzahl_erfolg: int, fehler: list[tuple[Path, str]]) -> None:
        text = self.tr("{0} Datei(en) erfolgreich verschlüsselt.").format(anzahl_erfolg)
        if fehler:
            text += "\n\n" + self.tr("{0} Datei(en) fehlgeschlagen:\n{1}").format(
                len(fehler), "\n".join(f"{pfad}: {msg}" for pfad, msg in fehler[:10])
            )
            QMessageBox.warning(self, self.tr("Teilweise fehlgeschlagen"), text)
        else:
            QMessageBox.information(self, self.tr("Fertig"), text)

    # -- Passwort-Log / password log -----------------------------------------

    def _log_gruppe(self) -> QGroupBox:
        self._log_anzeigen_feld = QCheckBox(self.tr("Passwörter anzeigen"))
        self._log_anzeigen_feld.toggled.connect(self._log_tabelle_aktualisieren)

        self._log_tabelle = QTableWidget(0, len(_LOG_SPALTEN))
        self._log_tabelle.setHorizontalHeaderLabels([self.tr(s) for s in _LOG_SPALTEN])
        # DE: ResizeToContents statt der Vorgabe -- sonst wird die
        #     Spaltenbreite nur an einer festen Startbreite bemessen und
        #     schneidet laengere Spaltentitel wie "Eigentümerpasswort" ab.
        # EN: ResizeToContents instead of the default -- otherwise column
        #     width is only sized to a fixed starting width and truncates
        #     longer column titles like "Eigentümerpasswort".
        self._log_tabelle.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._log_tabelle.horizontalHeader().setStretchLastSection(True)
        self._log_tabelle.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        btn_export = QPushButton(self.tr("Log exportieren …"))
        btn_export.clicked.connect(self._log_exportieren)
        btn_import = QPushButton(self.tr("Log importieren …"))
        btn_import.clicked.connect(self._log_importieren)
        btn_leeren = QPushButton(self.tr("Log leeren"))
        btn_leeren.clicked.connect(self._log_leeren)
        knopfzeile = QHBoxLayout()
        knopfzeile.addWidget(self._log_anzeigen_feld)
        knopfzeile.addStretch(1)
        knopfzeile.addWidget(btn_export)
        knopfzeile.addWidget(btn_import)
        knopfzeile.addWidget(btn_leeren)

        gruppe = QGroupBox(
            self.tr("Passwort-Log (Klartext -- nur zur eigenen Ablage, nicht verschlüsselt gespeichert)")
        )
        v = QVBoxLayout(gruppe)
        v.addLayout(knopfzeile)
        v.addWidget(self._log_tabelle, 1)
        return gruppe

    def _log_eintraege(self) -> list[LogEintrag]:
        return dicts_zu_log(einstellungen.passwort_log())

    def _log_ergaenzen(self, neue: list[LogEintrag]) -> None:
        if not neue:
            return
        alle = self._log_eintraege() + neue
        einstellungen.passwort_log_setzen(log_zu_dicts(alle))
        self._log_tabelle_aktualisieren()

    def _log_tabelle_aktualisieren(self) -> None:
        anzeigen = self._log_anzeigen_feld.isChecked() if hasattr(self, "_log_anzeigen_feld") else False

        def maske(text: str) -> str:
            return text if anzeigen or not text else "•" * 8

        eintraege = self._log_eintraege()
        self._log_tabelle.setRowCount(len(eintraege))
        for zeile, e in enumerate(eintraege):
            werte = (e.dateipfad, maske(e.nutzerpasswort), maske(e.eigentuemerpasswort), e.verfahren, e.zeitpunkt)
            for spalte, wert in enumerate(werte):
                self._log_tabelle.setItem(zeile, spalte, QTableWidgetItem(wert))

    def _log_exportieren(self) -> None:
        eintraege = self._log_eintraege()
        if not eintraege:
            QMessageBox.information(self, self.tr("Leeres Log"), self.tr("Es gibt noch keine Log-Einträge."))
            return
        ziel = speichern_dialog(self, self.tr("Log exportieren als"), "passwort_log.csv", self.tr("CSV-Datei (*.csv)"))
        if ziel is None:
            return
        ziel.write_text(log_als_csv(eintraege), encoding="utf-8")
        QMessageBox.information(self, self.tr("Fertig"), self.tr("Log exportiert nach:\n{0}").format(ziel))

    def _log_importieren(self) -> None:
        quelle = einzeln_oeffnen_dialog(self, self.tr("Log importieren"), self.tr("CSV-Datei (*.csv)"))
        if quelle is None:
            return
        neue = csv_als_log(quelle.read_text(encoding="utf-8"))
        if not neue:
            QMessageBox.information(self, self.tr("Leere Datei"), self.tr("In dieser Datei stehen keine gültigen Zeilen."))
            return
        self._log_ergaenzen(neue)
        QMessageBox.information(self, self.tr("Fertig"), self.tr("{0} Einträge importiert.").format(len(neue)))

    def _log_leeren(self) -> None:
        if not self._log_eintraege():
            return
        antwort = QMessageBox.question(
            self, self.tr("Log leeren?"), self.tr("Alle Log-Einträge unwiderruflich entfernen?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            einstellungen.passwort_log_setzen([])
            self._log_tabelle_aktualisieren()
