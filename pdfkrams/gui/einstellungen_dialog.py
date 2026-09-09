"""
DE: Einstellungen-Fenster (macOS: "Einstellungen …" im Anwendungsmenü,
    Cmd+,) -- aktuell Sprache und Maßeinheit. Änderungen wirken sofort
    (Maßeinheit) bzw. nach einem Neustart (Sprache -- ein Neuaufbau aller
    bereits erzeugten Fenster/Werkzeuge mit neuen Texten wäre deutlich
    aufwendiger und fehleranfälliger als ein einfacher Neustart-Hinweis).

EN: Preferences window (macOS: "Preferences …" in the application menu,
    Cmd+,) -- currently language and measurement unit. Changes take
    effect immediately (measurement unit) resp. after a restart
    (language -- rebuilding every already-created window/tool with new
    text would be considerably more complex and error-prone than a
    simple restart notice).
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QLabel, QVBoxLayout

from pdfkrams.einstellungen import MASSEINHEITEN, SPRACHEN, einstellungen


class EinstellungenDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Einstellungen"))
        self.setMinimumWidth(360)

        # DE: Merken, welche Sprache beim Oeffnen dieses Fensters aktiv
        #     war -- nur dann, wenn sich das aendert, macht ein
        #     Neustart-Hinweis Sinn.
        # EN: Remember which language was active when this window opened
        #     -- a restart notice only makes sense once that actually
        #     changes.
        self._sprache_beim_start = einstellungen.sprache()

        self._sprache_feld = QComboBox()
        for code, name in SPRACHEN.items():
            self._sprache_feld.addItem(name, code)
        self._sprache_feld.setCurrentIndex(self._sprache_feld.findData(einstellungen.sprache()))
        self._sprache_feld.currentIndexChanged.connect(self._sprache_geaendert)

        self._sprache_hinweis = QLabel()
        self._sprache_hinweis.setWordWrap(True)
        self._sprache_hinweis.setStyleSheet("color: gray;")

        self._masseinheit_feld = QComboBox()
        for code, name in MASSEINHEITEN.items():
            # DE: self.tr(name) -- Uebersetzung wird von Hand in der .ts
            #     ergaenzt (siehe main_window.py fuer denselben Ansatz).
            # EN: self.tr(name) -- translation added by hand to the .ts
            #     (see main_window.py for the same approach).
            self._masseinheit_feld.addItem(self.tr(name), code)
        self._masseinheit_feld.setCurrentIndex(self._masseinheit_feld.findData(einstellungen.masseinheit()))
        self._masseinheit_feld.currentIndexChanged.connect(self._masseinheit_geaendert)

        masseinheit_hinweis = QLabel(
            self.tr("Betrifft das Werkzeug „Seitenmaß normieren“ -- wird bewusst "
                   "nicht aus den Systemeinstellungen übernommen, da die "
                   "bearbeiteten PDFs aus jedem Land stammen können, unabhängig "
                   "davon, wie dieser Rechner eingestellt ist.")
        )
        masseinheit_hinweis.setWordWrap(True)
        masseinheit_hinweis.setStyleSheet("color: gray;")

        formular = QFormLayout()
        formular.addRow(self.tr("Sprache:"), self._sprache_feld)
        formular.addRow("", self._sprache_hinweis)
        formular.addRow(self.tr("Maßeinheit:"), self._masseinheit_feld)
        formular.addRow("", masseinheit_hinweis)

        layout = QVBoxLayout(self)
        layout.addLayout(formular)

    def _sprache_geaendert(self, _index: int) -> None:
        code = self._sprache_feld.currentData()
        einstellungen.sprache_setzen(code)
        geaendert = code != self._sprache_beim_start
        self._sprache_hinweis.setText(
            self.tr("Wird erst nach einem Neustart des Programms wirksam.") if geaendert else ""
        )

    def _masseinheit_geaendert(self, _index: int) -> None:
        einstellungen.masseinheit_setzen(self._masseinheit_feld.currentData())
