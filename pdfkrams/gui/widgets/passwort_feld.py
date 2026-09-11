"""
DE: Ein QLineEdit fuer Passworteingabe mit einem kleinen "anzeigen"-
    Kontrollkaesten daneben, der zwischen verdeckter und Klartext-
    Anzeige umschaltet -- an mehreren Stellen im Programm gebraucht
    (Passwort entfernen, Passwortschutz hinzufuegen), deshalb hier
    einmal gebaut statt mehrfach.

EN: A QLineEdit for password entry with a small "show" checkbox next to
    it that toggles between masked and plain-text display -- needed in
    several places in the app (remove password, add password
    protection), so built once here instead of repeatedly.
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget


class PasswortFeld(QWidget):
    """DE: Kombination aus Passwort-QLineEdit und Anzeigen-Kontrollkaestchen.
    EN: Combination of a password QLineEdit and a show checkbox."""

    def __init__(self, platzhalter: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._feld = QLineEdit()
        self._feld.setEchoMode(QLineEdit.EchoMode.Password)
        if platzhalter:
            self._feld.setPlaceholderText(platzhalter)
        self._anzeigen_feld = QCheckBox(self.tr("anzeigen"))
        self._anzeigen_feld.toggled.connect(self._echo_umschalten)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._feld, 1)
        layout.addWidget(self._anzeigen_feld)

    def _echo_umschalten(self, anzeigen: bool) -> None:
        self._feld.setEchoMode(QLineEdit.EchoMode.Normal if anzeigen else QLineEdit.EchoMode.Password)

    def text(self) -> str:
        return self._feld.text()

    def setText(self, text: str) -> None:  # noqa: N802 (Qt-Namenskonvention)
        self._feld.setText(text)

    def clear(self) -> None:
        self._feld.clear()


def passwort_abfragen(parent: QWidget, titel: str, beschriftung: str) -> str | None:
    """DE: Kleiner Dialog fuer eine einzelne Passworteingabe mit
        "anzeigen"-Umschalter (Ersatz fuer QInputDialog.getText mit
        EchoMode.Password, das keine solche Option hat). Liefert None,
        wenn abgebrochen oder das Feld leer gelassen wurde.
    EN: Small dialog for a single password entry with a "show" toggle
        (replacement for QInputDialog.getText with EchoMode.Password,
        which has no such option). Returns None if cancelled or the
        field was left empty."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(titel)
    feld = PasswortFeld()
    knoepfe = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    knoepfe.accepted.connect(dialog.accept)
    knoepfe.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel(beschriftung))
    layout.addWidget(feld)
    layout.addWidget(knoepfe)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    text = feld.text()
    return text or None
