# Third-party licenses / Drittanbieter-Lizenzen

**DE:** Diese Anwendung bündelt in ihren fertigen App-/exe-Builds (PyInstaller)
den Python-Interpreter und die folgenden Bibliotheken mit und verteilt sie unter
deren jeweiliger Lizenz. Die wichtigsten Punkte stehen darunter.

**EN:** This application bundles the Python interpreter and the following
libraries in its ready-made app/exe builds (PyInstaller) and redistributes them
under their respective licenses. The key points follow below.

| Component | Version | License | Project |
|---|---|---|---|
| PyMuPDF | 1.28.2 | **AGPL-3.0-only** (or commercial) | https://pymupdf.readthedocs.io/ |
| PySide6 / Essentials / Addons | 6.11.2 | **LGPL-3.0-only** (or GPL/commercial) | https://doc.qt.io/qtforpython/ |
| shiboken6 | 6.11.2 | **LGPL-3.0-only** | https://doc.qt.io/qtforpython/ |
| pikepdf | 10.13.0 | MPL-2.0 | https://github.com/pikepdf/pikepdf |
| Pillow | 12.3.0 | HPND (MIT-CMU) | https://python-pillow.github.io/ |
| NumPy | 2.5.3 | BSD-3-Clause | https://numpy.org/ |
| certifi | 2026.7.22 | MPL-2.0 | https://github.com/certifi/python-certifi |

Build tool (not bundled into the app): PyInstaller — GPL-2.0-or-later with a
bootloader exception that permits shipping the produced binaries under any
license.

## PyMuPDF – AGPL-3.0

**DE:** PyMuPDF steht unter der **AGPL-3.0**, nicht unter der GPL. Die GPLv3
erlaubt in **§13** ausdrücklich, ein GPLv3-Werk mit einem AGPLv3-Werk zu einem
kombinierten Gesamtwerk zu verbinden; für den AGPL-Teil gilt dann dessen §13
(Quelltext-Angebot bei Netzwerk-Nutzung). Diese Anwendung ist ein reines
Desktop-Programm ohne Netzwerkdienst, daher greift diese Zusatzpflicht praktisch
nicht. Der vollständige Quelltext dieser Anwendung ist ohnehin öffentlich. Wer
PyMuPDF ohne AGPL nutzen möchte, kann bei Artifex eine kommerzielle Lizenz
erwerben – das betrifft diese GPL-Anwendung nicht.

**EN:** PyMuPDF is licensed under the **AGPL-3.0**, not the GPL. GPLv3 **§13**
explicitly permits combining a GPLv3 work with an AGPLv3 work into a single
combined work; the AGPL's §13 (source offer on network use) then applies to the
AGPL part. This application is a pure desktop program with no network service,
so that extra obligation does not bite in practice, and the full source of this
application is public anyway. A commercial (non-AGPL) PyMuPDF license is
available from Artifex for those who need it – that does not affect this GPL
application.

## PySide6 / shiboken6 – LGPL-3.0

**DE:** Qt for Python (PySide6) und shiboken6 stehen unter der **LGPL-3.0**. Die
LGPL verlangt, dass Nutzer die Bibliothek durch eine eigene, veränderte Fassung
ersetzen können. In den fertigen Builds liegen PySide6/Qt als eigenständige,
austauschbare Shared Libraries im App-Paket; zusätzlich ist der komplette
Quelltext dieser Anwendung verfügbar, sodass sie sich mit einer anderen
PySide6-Fassung neu bauen lässt. Damit ist die LGPL-Pflicht erfüllt.

**EN:** Qt for Python (PySide6) and shiboken6 are licensed under the
**LGPL-3.0**. The LGPL requires that users be able to replace the library with
their own modified version. In the ready-made builds, PySide6/Qt ship as
separate, replaceable shared libraries inside the app bundle; additionally the
full source of this application is available, so it can be rebuilt against a
different PySide6 version. This satisfies the LGPL requirement.

## MPL-2.0 / BSD / HPND

**DE:** pikepdf und certifi (MPL-2.0), NumPy (BSD-3-Clause) und Pillow (HPND)
sind mit der GPLv3 kombinierbar. Die vollständigen Lizenztexte liegen jeweils in
den installierten Paketen bzw. in den gebündelten Builds bei.

**EN:** pikepdf and certifi (MPL-2.0), NumPy (BSD-3-Clause) and Pillow (HPND) are
compatible with the GPLv3. The full license texts are included with each
installed package and in the bundled builds.

---

**DE:** Dieses Programm selbst steht unter der **GPL-3.0** – siehe `LICENSE`.
**EN:** This program itself is licensed under the **GPL-3.0** – see `LICENSE`.
