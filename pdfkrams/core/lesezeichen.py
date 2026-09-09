"""
DE: Erzeugt aus den pro Seite gesetzten Lesezeichen-Titeln (siehe
    WorkingPage.lesezeichen_titel/lesezeichen_ebene) eine fuer
    fitz.Document.set_toc() gueltige Gliederung.

    PDF-Gliederungen erlauben pro Eintrag hoechstens eine Ebene mehr als
    die bisher tiefste erreichte Ebene (z. B. darf nach einem Kapitel
    (Ebene 1) direkt ein Unterkapitel (Ebene 2) kommen, aber kein
    Unter-Unterkapitel (Ebene 3), solange noch keine Ebene 2 aufgetreten
    ist -- fitz.set_toc() bricht sonst mit einem Fehler ab). Deshalb wird
    hier defensiv geklammert: ein Unterkapitel ganz am Anfang (bevor
    ueberhaupt ein Kapitel gesetzt wurde) wird automatisch zu einem
    Kapitel hochgestuft, statt den Export scheitern zu lassen.

EN: Builds a table-of-contents structure valid for
    fitz.Document.set_toc() from the per-page bookmark titles (see
    WorkingPage.lesezeichen_titel/lesezeichen_ebene).

    PDF outlines allow each entry to be at most one level deeper than the
    deepest level reached so far (e.g. a sub-chapter (level 2) may
    directly follow a chapter (level 1), but not a sub-sub-chapter
    (level 3) while no level 2 has occurred yet -- fitz.set_toc()
    otherwise aborts with an error). Hence the defensive clamping here: a
    sub-chapter right at the start (before any chapter was set) is
    automatically promoted to a chapter, instead of letting the export
    fail.
"""

from __future__ import annotations


def toc_erzeugen(eintraege: list[tuple[int, str, int]]) -> list[list]:
    """
    DE: `eintraege` als Liste von (ebene, titel, seitennummer) in
        Seitenreihenfolge -- `seitennummer` 1-basiert wie von
        fitz.Document.set_toc() erwartet. Liefert eine geklammerte,
        garantiert gueltige Gliederungsliste.
    EN: `eintraege` as a list of (level, title, page_number) in page
        order -- `page_number` 1-based as expected by
        fitz.Document.set_toc(). Returns a clamped, guaranteed-valid
        outline list.
    """
    ergebnis: list[list] = []
    erlaubte_hoechstebene = 1
    for ebene, titel, seite in eintraege:
        ebene = min(ebene, erlaubte_hoechstebene)
        ergebnis.append([ebene, titel, seite])
        erlaubte_hoechstebene = ebene + 1
    return ergebnis
