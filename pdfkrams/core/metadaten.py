"""
DE: Dokumentweite PDF-Metadaten -- anders als alle anderen Werkzeuge
    (die pro Seite arbeiten) gilt hier ein einziger Satz Rohdaten fuer
    das gesamte Dokument (Titel, Autor, Anbieter, Produkt, Version,
    Releasedatum, Stichwoerter), gespeichert als einfaches dict auf
    PageListWidget (siehe gui/widgets/page_list.py).

    PDF kennt nur eine feste Anzahl Standardfelder (Titel, Autor, Thema,
    Stichwoerter) -- Produkt/Version/Releasedatum/Anbieter gibt es dort
    nicht eigens. Deshalb hier zusammengefuehrt: Autor+Anbieter -> das
    PDF-Feld "Autor"; Produkt -> "Thema"; Version+Releasedatum+die vom
    Nutzer eingegebenen Stichwoerter -> "Stichwoerter". Reine Zeichenketten-
    Logik, keine Qt-Abhaengigkeit (das schon formatierte Datum wird von
    aussen hereingereicht, da die Formateinstellung in pdfkrams/
    einstellungen.py liegt, welches Qt fuer QSettings braucht).

EN: Document-wide PDF metadata -- unlike every other tool (which works
    per page), a single set of raw fields applies to the whole document
    (title, author, provider, product, version, release date, keywords),
    stored as a plain dict on PageListWidget (see
    gui/widgets/page_list.py).

    PDF only has a fixed number of standard fields (title, author,
    subject, keywords) -- there's no dedicated field for
    product/version/release date/provider. Hence merged here:
    author+provider -> the PDF "author" field; product -> "subject";
    version+release date+the user's own keywords -> "keywords". Pure
    string logic, no Qt dependency (the already-formatted date is passed
    in from outside, since the format setting lives in
    pdfkrams/einstellungen.py, which needs Qt for QSettings).
"""

from __future__ import annotations

import re

ROHFELDER = ("titel", "autor", "anbieter", "produkt", "version", "releasedatum", "stichwoerter")

_DATEINAME_UNZULAESSIG = re.compile(r'[/\\:*?"<>|]')


def leere_rohdaten() -> dict[str, str]:
    """DE: Ein frisches, leeres Rohdaten-dict mit allen bekannten Feldern.
    EN: A fresh, empty raw-data dict with all known fields."""
    return {feld: "" for feld in ROHFELDER}


def pdf_felder(rohdaten: dict[str, str], datum_formatiert: str) -> dict[str, str]:
    """
    DE: Fuehrt die Rohfelder zu den vier PDF-Standardfeldern zusammen.
        Leere Felder werden ausgelassen (kein "None"/leere Strings im
        Ergebnis). `datum_formatiert` ist das Releasedatum bereits als
        Text im vom Nutzer eingestellten Format (leer, wenn kein Datum
        gesetzt ist).
    EN: Merges the raw fields into the four standard PDF fields. Empty
        fields are omitted (no "None"/empty strings in the result).
        `datum_formatiert` is the release date already rendered as text
        in the user's configured format (empty if no date is set).
    """
    autor_teile = [t for t in (rohdaten.get("autor", ""), rohdaten.get("anbieter", "")) if t]
    stichwort_teile = []
    if rohdaten.get("version"):
        stichwort_teile.append(f"Version: {rohdaten['version']}")
    if datum_formatiert:
        stichwort_teile.append(datum_formatiert)
    if rohdaten.get("stichwoerter"):
        stichwort_teile.append(rohdaten["stichwoerter"])

    ergebnis: dict[str, str] = {}
    if rohdaten.get("titel"):
        ergebnis["title"] = rohdaten["titel"]
    if autor_teile:
        ergebnis["author"] = ", ".join(autor_teile)
    if rohdaten.get("produkt"):
        ergebnis["subject"] = rohdaten["produkt"]
    if stichwort_teile:
        ergebnis["keywords"] = " | ".join(stichwort_teile)
    return ergebnis


def dateiname_vorschlagen(rohdaten: dict[str, str], datum_formatiert: str) -> str:
    """
    DE: Baut aus Produkt, Titel, Version und Releasedatum (in dieser
        Reihenfolge, leere Teile werden ausgelassen) einen
        Dateinamensvorschlag, z. B.
        "Gigaset E290 - Bedienungsanleitung v1.2 (26-09).pdf". Fehlt
        Titel UND Produkt, wird ein leerer String zurueckgegeben
        (Aufrufer soll dann seinen eigenen Standardnamen verwenden).
    EN: Builds a suggested filename from product, title, version, and
        release date (in this order, empty parts omitted), e.g.
        "Gigaset E290 - Bedienungsanleitung v1.2 (26-09).pdf". If both
        title AND product are missing, returns an empty string (caller
        should fall back to its own default name then).
    """
    produkt = rohdaten.get("produkt", "").strip()
    titel = rohdaten.get("titel", "").strip()
    version = rohdaten.get("version", "").strip()

    kern_teile = [t for t in (produkt, titel) if t]
    if not kern_teile:
        return ""
    name = " - ".join(kern_teile)
    if version:
        name += f" v{version}"
    if datum_formatiert:
        name += f" ({datum_formatiert})"

    name = _DATEINAME_UNZULAESSIG.sub("_", name).strip()
    return f"{name}.pdf"
