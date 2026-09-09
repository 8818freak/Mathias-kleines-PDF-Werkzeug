"""
DE: Kleiner, von mehreren Werkzeugen gemeinsam genutzter Helfer, um ein
    bereits im Speicher vorliegendes PIL-Bild (z. B. ein fertig
    gerendertes Vorschaubild) als QPixmap fuer die Anzeige umzuwandeln.

EN: Small helper shared by several tools to convert an already in-memory
    PIL image (e.g. an already-rendered preview image) into a QPixmap for
    display.
"""

from __future__ import annotations

from PIL import Image
from PySide6.QtGui import QImage, QPixmap


def pil_zu_qpixmap(bild: Image.Image) -> QPixmap:
    """DE: Ein PIL-Bild in eine anzeigbare QPixmap umwandeln.
    EN: Convert a PIL image into a displayable QPixmap."""
    rgb = bild.convert("RGB")
    qimg = QImage(rgb.tobytes(), rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())
