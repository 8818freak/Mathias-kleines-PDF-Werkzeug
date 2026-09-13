"""
DE: Prueft ueber GitHubs oeffentliche Releases-API, ob eine neuere Version
    von "Mathias' kleines PDF-Werkzeug" verfuegbar ist. Rein optional und
    standardmaessig AUSGESCHALTET (siehe einstellungen.py's
    updates_pruefen()) -- ist die Funktion aus, braucht die App
    ueberhaupt keine Internetverbindung, wie im README beworben. Nur bei
    ausdruecklich eingeschalteter Prüfung wird beim Programmstart einmal
    im Hintergrund (siehe gui/widgets/hintergrund.py's
    im_hintergrund_still_ausfuehren()) eine einzelne, unauthentifizierte
    HTTPS-Anfrage an GitHub gestellt.

EN: Checks via GitHub's public releases API whether a newer version of
    "Mathias' kleines PDF-Werkzeug" is available. Purely optional and OFF
    by default (see einstellungen.py's updates_pruefen()) -- with the
    feature off, the app needs no internet connection at all, as
    advertised in the README. Only when explicitly enabled does the app
    make a single, unauthenticated HTTPS request to GitHub once on
    startup, in the background (see gui/widgets/hintergrund.py's
    im_hintergrund_still_ausfuehren()).
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

from ..info import VERSION

# DE: Oeffentliche, unauthentifizierte GitHub-API -- kein Token noetig,
#     funktioniert auch fuer ein privates Repo NICHT (dafuer braeuchte es
#     Auth); solange das Repo privat bleibt, liefert dieser Aufruf 404 und
#     die Pruefung schlaegt einfach fehl (kein Absturz, siehe
#     neueste_version_pruefen()'s try/except).
# EN: Public, unauthenticated GitHub API -- no token needed, but also
#     doesn't work for a PRIVATE repo (that would require auth); as long
#     as the repo stays private, this call returns 404 and the check
#     simply fails (no crash, see neueste_version_pruefen()'s try/except).
_API_URL = "https://api.github.com/repos/8818freak/Mathias-kleines-PDF-Werkzeug/releases/latest"
_TIMEOUT_SEKUNDEN = 5


@dataclass
class UpdateInfo:
    version: str
    url: str


def _version_tupel(text: str) -> tuple[int, ...]:
    """DE: "v1.12.1" oder "1.12" in ein vergleichbares Zahlen-Tupel umwandeln.
    EN: Turn "v1.12.1" or "1.12" into a comparable tuple of numbers."""
    ziffern = re.findall(r"\d+", text)
    return tuple(int(z) for z in ziffern) if ziffern else (0,)


def neueste_version_pruefen(_fortschritt=None) -> UpdateInfo | None:
    """
    DE: Fragt die neueste GitHub-Release ab und liefert eine UpdateInfo,
        falls deren Version groesser als die eigene ist -- sonst None.
        Jeder Fehler (kein Netz, Timeout, Repo (noch) privat/nicht
        gefunden, unerwartetes Antwortformat) liefert ebenfalls still
        None, statt eine Ausnahme auszuloesen -- eine fehlgeschlagene
        Update-Pruefung soll die App niemals stoeren. `_fortschritt` wird
        ignoriert, ist aber noetig, damit die Funktion zur Schnittstelle
        von gui/widgets/hintergrund.py passt.

    EN: Queries the latest GitHub release and returns an UpdateInfo if its
        version is greater than our own -- otherwise None. Any error (no
        network, timeout, repo (still) private/not found, unexpected
        response shape) also silently returns None instead of raising --
        a failed update check should never disrupt the app. `_fortschritt`
        is ignored, but needed so the function matches the interface of
        gui/widgets/hintergrund.py.
    """
    try:
        anfrage = urllib.request.Request(
            _API_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "pdfkrams-update-check"}
        )
        with urllib.request.urlopen(anfrage, timeout=_TIMEOUT_SEKUNDEN) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
        tag = daten.get("tag_name") or ""
        url = daten.get("html_url") or ""
        if not tag:
            return None
        if _version_tupel(tag) > _version_tupel(VERSION):
            return UpdateInfo(version=tag.lstrip("vV"), url=url)
        return None
    except Exception:  # noqa: BLE001 -- Update-Pruefung darf niemals die App stoeren
        return None
