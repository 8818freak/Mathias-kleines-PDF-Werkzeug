"""
DE: Einstiegspunkt der Anwendung.
EN: Application entry point.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pdfkrams.gui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    fenster = MainWindow()
    fenster.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
