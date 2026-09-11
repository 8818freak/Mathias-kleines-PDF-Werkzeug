"""
DE: Werkzeug "PDF reparieren & entsperren": eigenstaendige Aktionen fuer
    beliebige, bereits vorhandene PDF-Dateien (nicht die gemeinsame
    Seitenliste) -- passend zu den aehnlich aufgebauten Standalone-
    Abschnitten im Werkzeug "PDF verkleinern & PDF/A". Reparieren,
    Passwort entfernen (bekanntes Passwort), sowie Passwort wieder-
    herstellen (VERGESSENES Passwort -- Woerterbuch-Angriff und
    Brute-Force, siehe core/passwort_wiederherstellung.py).

EN: "Repair & unlock PDF" tool: standalone actions for any existing PDF
    file (not the shared page list) -- matching the similarly built
    standalone sections in the "Shrink PDF & PDF/A" tool. Repair, remove
    password (known password), and recover password (FORGOTTEN
    password -- dictionary attack and brute force, see
    core/passwort_wiederherstellung.py).
"""

from __future__ import annotations

from pathlib import Path

import pikepdf
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

from pdfkrams.core.passwort_log import LogEintrag, dicts_zu_log, log_zu_dicts
from pdfkrams.core.passwort_wiederherstellung import ZEICHENSAETZE, brute_force, geschwindigkeit_messen, kombinationsanzahl, woerterbuch_angriff
from pdfkrams.core.reparatur import ReparaturFehlgeschlagen, ist_verschluesselt, passwort_entfernen, pdf_reparieren
from pdfkrams.einstellungen import einstellungen
from pdfkrams.gui.widgets.datei_dialoge import einzeln_oeffnen_dialog, speichern_dialog
from pdfkrams.gui.widgets.hintergrund import im_hintergrund_ausfuehren
from pdfkrams.gui.widgets.page_list import PageListWidget
from pdfkrams.gui.widgets.passwort_feld import passwort_abfragen
from pdfkrams.gui.widgets.wiederherstellung_dialog import dauer_text, wiederherstellung_ausfuehren

# DE: Anzeigename -> interner Schluessel (siehe core/passwort_wiederherstellung.py's ZEICHENSAETZE).
# EN: Display name -> internal key (see core/passwort_wiederherstellung.py's ZEICHENSAETZE).
_ZEICHENSATZ_ANZEIGE: dict[str, str] = {
    "Ziffern (0-9)": "ziffern",
    "Kleinbuchstaben (a-z)": "kleinbuchstaben",
    "Großbuchstaben (A-Z)": "grossbuchstaben",
    "Sonderzeichen (!\"#$% …)": "sonderzeichen",
}


class ReparaturToolWidget(QWidget):
    """
    DE: GUI-Seite fuer PDF-Reparatur und Passwort-Entfernung.
    EN: GUI page for PDF repair and password removal.
    """

    def __init__(self, liste: PageListWidget, parent=None) -> None:
        super().__init__(parent)
        self.liste = liste

        # -- Reparieren / repair --------------------------------------------
        reparatur_hinweis = QLabel(
            self.tr("Repariert eine beschädigte PDF-Datei, die sich nicht mehr öffnen "
                   "lässt -- rekonstruiert dabei eine defekte Querverweistabelle bzw. "
                   "einen fehlerhaften Dateiabschluss, die häufigsten Ursachen für "
                   "\"PDF lässt sich nicht öffnen\". Bei sehr stark beschädigten Dateien "
                   "(z. B. beim Speichern abgebrochen, ohne jede Seitenstruktur) ist "
                   "auch damit keine Rettung möglich -- eine Reparatur ersetzt kein "
                   "Backup.")
        )
        reparatur_hinweis.setWordWrap(True)
        btn_reparieren = QPushButton(self.tr("Beschädigte PDF-Datei reparieren …"))
        btn_reparieren.clicked.connect(self._reparieren)

        reparatur_gruppe = QGroupBox(self.tr("PDF reparieren"))
        reparatur_layout = QVBoxLayout(reparatur_gruppe)
        reparatur_layout.addWidget(reparatur_hinweis)
        reparatur_layout.addWidget(btn_reparieren)

        # -- Passwort entfernen / remove password ---------------------------
        passwort_hinweis = QLabel(
            self.tr("Entfernt den Passwortschutz einer PDF-Datei -- das Passwort muss "
                   "dafür bekannt sein, es wird nicht erraten oder geknackt.")
        )
        passwort_hinweis.setWordWrap(True)
        btn_passwort = QPushButton(self.tr("Passwortgeschützte PDF-Datei entsperren …"))
        btn_passwort.clicked.connect(self._passwort_entfernen)

        passwort_gruppe = QGroupBox(self.tr("Passwort entfernen"))
        passwort_layout = QVBoxLayout(passwort_gruppe)
        passwort_layout.addWidget(passwort_hinweis)
        passwort_layout.addWidget(btn_passwort)

        layout = QVBoxLayout(self)
        layout.addWidget(reparatur_gruppe)
        layout.addWidget(passwort_gruppe)
        layout.addWidget(self._wiederherstellung_gruppe())
        layout.addStretch(1)

    # -- Reparieren / repair --------------------------------------------

    def _reparieren(self) -> None:
        quelle = einzeln_oeffnen_dialog(self, self.tr("Beschädigte PDF-Datei wählen"), self.tr("PDF-Datei (*.pdf)"))
        if quelle is None:
            return
        ziel = speichern_dialog(
            self, self.tr("Reparierte PDF speichern unter"), quelle.stem + "_repariert.pdf",
            self.tr("PDF-Datei (*.pdf)"),
        )
        if ziel is None:
            return
        try:
            anzahl = im_hintergrund_ausfuehren(
                self, self.tr("PDF wird repariert …"), lambda _f: pdf_reparieren(quelle, ziel),
            )
        except ReparaturFehlgeschlagen as exc:
            QMessageBox.critical(
                self, self.tr("Reparatur fehlgeschlagen"),
                self.tr("Diese Datei ist zu stark beschädigt, um sie automatisch zu "
                       "reparieren:\n\n{0}").format(exc),
            )
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Reparatur fehlgeschlagen"), str(exc))
            return
        QMessageBox.information(
            self, self.tr("Fertig"),
            self.tr("{0} Seiten gerettet, gespeichert unter:\n{1}").format(anzahl, ziel),
        )

    # -- Passwort entfernen / remove password ---------------------------

    def _passwort_entfernen(self) -> None:
        quelle = einzeln_oeffnen_dialog(self, self.tr("Passwortgeschützte PDF-Datei wählen"), self.tr("PDF-Datei (*.pdf)"))
        if quelle is None:
            return
        if not ist_verschluesselt(quelle):
            QMessageBox.information(
                self, self.tr("Kein Passwort"),
                self.tr("Diese Datei ist nicht passwortgeschützt -- es gibt nichts zu entfernen."),
            )
            return
        passwort = passwort_abfragen(self, self.tr("Passwort erforderlich"), self.tr("Passwort dieser PDF-Datei:"))
        if passwort is None:
            return
        ziel = speichern_dialog(
            self, self.tr("Entsperrte PDF speichern unter"), quelle.stem + "_entsperrt.pdf",
            self.tr("PDF-Datei (*.pdf)"),
        )
        if ziel is None:
            return
        try:
            im_hintergrund_ausfuehren(
                self, self.tr("Passwort wird entfernt …"), lambda _f: passwort_entfernen(quelle, ziel, passwort),
            )
        except pikepdf.PasswordError:
            QMessageBox.critical(self, self.tr("Falsches Passwort"), self.tr("Dieses Passwort ist nicht korrekt."))
            return
        except Exception as exc:  # noqa: BLE001 -- Fehler dem Nutzer verstaendlich zeigen
            QMessageBox.critical(self, self.tr("Fehlgeschlagen"), str(exc))
            return
        QMessageBox.information(self, self.tr("Fertig"), self.tr("Entsperrte PDF gespeichert unter:\n{0}").format(ziel))

    # -- Passwort wiederherstellen / recover password ------------------------

    def _wiederherstellung_gruppe(self) -> QGroupBox:
        hinweis = QLabel(
            self.tr("Für ein wirklich VERGESSENES Passwort (nicht bekannt, auch nicht in "
                   "„Passwort entfernen“ oben) -- probiert entweder eine Liste möglicher "
                   "Passwörter durch (Wörterbuch-Angriff, schnell) oder ALLE Kombinationen "
                   "aus gewählten Zeichenarten (Brute-Force, wächst mit der Länge extrem "
                   "schnell -- vorher schätzen lassen, bevor ein aussichtsloser Lauf "
                   "gestartet wird).")
        )
        hinweis.setWordWrap(True)

        self._wh_datei: Path | None = None
        self._wh_datei_anzeige = QLabel(self.tr("(keine Datei gewählt)"))
        self._wh_datei_anzeige.setStyleSheet("color: gray;")
        btn_datei = QPushButton(self.tr("PDF-Datei wählen …"))
        btn_datei.clicked.connect(self._wh_datei_waehlen)
        datei_zeile = QHBoxLayout()
        datei_zeile.addWidget(btn_datei)
        datei_zeile.addWidget(self._wh_datei_anzeige, 1)

        # -- Woerterbuch-Angriff --
        self._wb_log_feld = QCheckBox(self.tr("Eigenes Passwort-Log (siehe Werkzeug „Passwortschutz“) durchsuchen"))
        self._wb_log_feld.setChecked(True)
        btn_woerterbuch = QPushButton(self.tr("+ Wortliste wählen && versuchen …"))
        btn_woerterbuch.clicked.connect(self._woerterbuch_versuchen)

        woerterbuch_gruppe = QGroupBox(self.tr("Wörterbuch-Angriff"))
        wb_layout = QVBoxLayout(woerterbuch_gruppe)
        wb_layout.addWidget(self._wb_log_feld)
        wb_layout.addWidget(btn_woerterbuch)

        # -- Brute-Force --
        self._bf_felder: dict[str, QCheckBox] = {}
        zeichenarten_zeile = QHBoxLayout()
        for anzeige, schluessel in _ZEICHENSATZ_ANZEIGE.items():
            feld = QCheckBox(self.tr(anzeige))
            feld.setChecked(schluessel in ("ziffern", "kleinbuchstaben"))
            self._bf_felder[schluessel] = feld
            zeichenarten_zeile.addWidget(feld)

        laenge_zeile = QHBoxLayout()
        laenge_zeile.addWidget(QLabel(self.tr("Länge von")))
        self._bf_min_feld = QSpinBox()
        self._bf_min_feld.setRange(1, 32)
        self._bf_min_feld.setValue(1)
        laenge_zeile.addWidget(self._bf_min_feld)
        laenge_zeile.addWidget(QLabel(self.tr("bis")))
        self._bf_max_feld = QSpinBox()
        self._bf_max_feld.setRange(1, 32)
        self._bf_max_feld.setValue(4)
        laenge_zeile.addWidget(self._bf_max_feld)
        laenge_zeile.addStretch(1)

        self._bf_schaetzung_anzeige = QLabel("")
        self._bf_schaetzung_anzeige.setWordWrap(True)
        btn_schaetzen = QPushButton(self.tr("Suchraum && Dauer schätzen"))
        btn_schaetzen.clicked.connect(self._brute_force_schaetzen)
        btn_starten = QPushButton(self.tr("Suche starten …"))
        btn_starten.clicked.connect(self._brute_force_starten)
        knopf_zeile = QHBoxLayout()
        knopf_zeile.addWidget(btn_schaetzen)
        knopf_zeile.addWidget(btn_starten)

        brute_force_gruppe = QGroupBox(self.tr("Brute-Force nach Zeichenvorrat + Länge"))
        bf_layout = QVBoxLayout(brute_force_gruppe)
        bf_layout.addLayout(zeichenarten_zeile)
        bf_layout.addLayout(laenge_zeile)
        bf_layout.addWidget(self._bf_schaetzung_anzeige)
        bf_layout.addLayout(knopf_zeile)

        gruppe = QGroupBox(self.tr("Passwort wiederherstellen (vergessenes Passwort)"))
        v = QVBoxLayout(gruppe)
        v.addWidget(hinweis)
        v.addLayout(datei_zeile)
        v.addWidget(woerterbuch_gruppe)
        v.addWidget(brute_force_gruppe)
        return gruppe

    def _wh_datei_waehlen(self) -> None:
        pfad = einzeln_oeffnen_dialog(self, self.tr("PDF-Datei wählen"), self.tr("PDF-Datei (*.pdf)"))
        if pfad is None:
            return
        self._wh_datei = pfad
        self._wh_datei_anzeige.setText(str(pfad))
        self._wh_datei_anzeige.setStyleSheet("")

    def _wh_datei_pruefen(self) -> Path | None:
        if self._wh_datei is None:
            QMessageBox.information(self, self.tr("Keine Datei"), self.tr("Bitte zuerst eine PDF-Datei wählen."))
            return None
        return self._wh_datei

    def _wiederherstellung_erfolg(self, datei: Path, passwort: str) -> None:
        antwort = QMessageBox.question(
            self, self.tr("Passwort gefunden!"),
            self.tr("Das Passwort lautet:\n\n{0}\n\nIn das Passwort-Log übernehmen "
                   "(siehe Werkzeug „Passwortschutz“)?").format(passwort),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if antwort == QMessageBox.StandardButton.Yes:
            eintraege = dicts_zu_log(einstellungen.passwort_log())
            eintraege.append(LogEintrag.jetzt(datei, passwort, "", self.tr("wiederhergestellt")))
            einstellungen.passwort_log_setzen(log_zu_dicts(eintraege))

    def _woerterbuch_versuchen(self) -> None:
        datei = self._wh_datei_pruefen()
        if datei is None:
            return
        wortliste_datei = einzeln_oeffnen_dialog(self, self.tr("Wortliste wählen (optional -- Abbrechen für nur Log)"), self.tr("Textdatei (*.txt)"))
        kandidaten: list[str] = []
        if wortliste_datei is not None:
            kandidaten.extend(
                zeile.strip() for zeile in wortliste_datei.read_text(encoding="utf-8", errors="ignore").splitlines()
            )
        if self._wb_log_feld.isChecked():
            kandidaten.extend(e.nutzerpasswort for e in dicts_zu_log(einstellungen.passwort_log()))
            kandidaten.extend(e.eigentuemerpasswort for e in dicts_zu_log(einstellungen.passwort_log()))
        kandidaten = [k for k in dict.fromkeys(kandidaten) if k]
        if not kandidaten:
            QMessageBox.information(
                self, self.tr("Keine Kandidaten"),
                self.tr("Weder eine Wortliste noch (angehakte) Log-Einträge mit Passwörtern vorhanden."),
            )
            return
        gefunden, abgebrochen = wiederherstellung_ausfuehren(
            self, self.tr("Wörterbuch-Angriff läuft …"),
            lambda fortschritt, abbrechen: woerterbuch_angriff(datei, kandidaten, fortschritt=fortschritt, abbrechen=abbrechen),
        )
        if gefunden is not None:
            self._wiederherstellung_erfolg(datei, gefunden)
        elif not abgebrochen:
            QMessageBox.information(
                self, self.tr("Kein Treffer"),
                self.tr("Keines der {0} Kandidaten-Passwörter passt.").format(len(kandidaten)),
            )

    def _brute_force_zeichenvorrat(self) -> str:
        return "".join(ZEICHENSAETZE[schluessel] for schluessel, feld in self._bf_felder.items() if feld.isChecked())

    def _brute_force_schaetzen(self) -> None:
        datei = self._wh_datei_pruefen()
        if datei is None:
            return
        vorrat = self._brute_force_zeichenvorrat()
        if not vorrat:
            QMessageBox.information(self, self.tr("Keine Zeichenart"), self.tr("Bitte mindestens eine Zeichenart auswählen."))
            return
        min_laenge, max_laenge = self._bf_min_feld.value(), self._bf_max_feld.value()
        if min_laenge > max_laenge:
            QMessageBox.information(self, self.tr("Ungültiger Bereich"), self.tr("Die Mindestlänge darf nicht größer als die Höchstlänge sein."))
            return
        anzahl = kombinationsanzahl(vorrat, min_laenge, max_laenge)
        rate = im_hintergrund_ausfuehren(self, self.tr("Geschwindigkeit wird gemessen …"), lambda _f: geschwindigkeit_messen(datei))
        sekunden = anzahl / rate if rate > 0 else 0
        self._bf_schaetzung_anzeige.setText(
            self.tr("{0} Kombinationen, ca. {1} Versuche/s an dieser Datei -- geschätzte Dauer: {2}").format(
                f"{anzahl:,}".replace(",", "."), round(rate), dauer_text(sekunden)
            )
        )

    def _brute_force_starten(self) -> None:
        datei = self._wh_datei_pruefen()
        if datei is None:
            return
        vorrat = self._brute_force_zeichenvorrat()
        if not vorrat:
            QMessageBox.information(self, self.tr("Keine Zeichenart"), self.tr("Bitte mindestens eine Zeichenart auswählen."))
            return
        min_laenge, max_laenge = self._bf_min_feld.value(), self._bf_max_feld.value()
        if min_laenge > max_laenge:
            QMessageBox.information(self, self.tr("Ungültiger Bereich"), self.tr("Die Mindestlänge darf nicht größer als die Höchstlänge sein."))
            return
        anzahl = kombinationsanzahl(vorrat, min_laenge, max_laenge)
        antwort = QMessageBox.question(
            self, self.tr("Suche wirklich starten?"),
            self.tr("{0} Kombinationen werden ausprobiert -- das kann sehr lange dauern und "
                   "lässt sich jederzeit über den Abbrechen-Knopf im Fortschrittsfenster "
                   "stoppen. Fortfahren?").format(f"{anzahl:,}".replace(",", ".")),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if antwort != QMessageBox.StandardButton.Yes:
            return
        gefunden, abgebrochen = wiederherstellung_ausfuehren(
            self, self.tr("Brute-Force läuft …"),
            lambda fortschritt, abbrechen: brute_force(datei, vorrat, min_laenge, max_laenge, fortschritt=fortschritt, abbrechen=abbrechen),
        )
        if gefunden is not None:
            self._wiederherstellung_erfolg(datei, gefunden)
        elif not abgebrochen:
            QMessageBox.information(
                self, self.tr("Kein Treffer"),
                self.tr("Kein Passwort in diesem Zeichenraum/Längenbereich gefunden."),
            )
