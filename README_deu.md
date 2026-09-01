<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📦 Erkennt, installiert und aktualisiert das gesamte HYDRA-UMC/URTC-Ökosystem von Hand

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only CLI core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
</p>

> **Visueller Desktopmodus:** die Standard-Desktopoberflaeche nutzt jetzt
> **Qt Quick / QML** mit der optionalen GUI-Laufzeit `PySide6`. Kern und
> `--cli` bleiben fur eine headless CM5 reine Standardbibliothek.
>
> **Windows-Start und Nachweise:** offnen Sie `run-gui.vbs` (oder `run.bat`
> ohne Argumente) fur den konsolenfreien Desktop-Client. Das Update-Panel zeigt
> echte Checkpoints fur Vorabprufung, Quelle, Manifest, Build-test und Abschluss
> mit erfassten Nachweisen; `run.bat --cli ...` behalt das Diagnose-Terminal.
> Installieren ist nur ohne Checkout aktiv, Aktualisieren nur bei neuerer
> GitHub-Version. Wahrend einer bestaetigten Aktion ersetzen Checkpoints die
> Projektsteuerung; eine neue Projektauswahl stellt sie wieder her.
> **Alle fehlenden installieren** und **Alle veralteten aktualisieren** sind
> separat bestaetigte, sequenzielle Sammelaktionen auf Basis desselben realen
> Zustands und Sicherheitswegs.

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

HYDRA-UMC-UPDATER ist ein kleines Tool - Fenster-GUI standardmäßig, volle
CLI mit `--cli` - das sowohl auf dem echten CM5 als auch auf dem eigenen
Windows/Linux/macOS-Rechner eines Entwicklers laufen soll (jeder
Workspace mit demselben Checkout-Layout) und drei Fragen für jedes der
anderen 44 Ökosystem-Projekte beantwortet:

1. **Was ist hier tatsächlich installiert, und in welcher Version?**
2. **Was ist die neueste auf GitHub veröffentlichte Version?**
3. **Falls GitHub neuer ist, lass mich GENAU DIESES Projekt von Hand aktualisieren.**

Dieser letzte Punkt ist bewusst und nicht verhandelbar: Dieses Tool
aktualisiert nie mehr als ein Projekt pro Befehl, und nie aus eigener
Initiative. Eine Roboter-Steuerzelle ist nicht etwas, das sich über Nacht
von selbst aktualisieren sollte - jede echte Aktualisierung ist ein
Befehl (oder ein Klick auf eine Schaltfläche, für eine in der GUI-Tabelle
ausgewählte Zeile), den eine Person ausgelöst hat, für ein benanntes
Projekt, dessen Ergebnis sie sehen kann, bevor sie das nächste anfasst.

Auch gehören nicht alle 44 Projekte auf den CM5 - die meisten
URTC-präfixierten Repos und einige von HYDRA-UMC sind Werkzeuge, die ein
Entwickler auf dem eigenen PC ausführt (Firmware wird VOM Arbeitsplatz
kompiliert und geflasht, nicht AUF der Zelle gebaut), oder Apps, die auf
einem Handy/einer Uhr installiert werden. Das eigene `deploy`-Feld von
`registry.py` verzeichnet, welches welches ist (siehe Abschnitt 3), und
die Projekttabelle der GUI filtert danach - standardmäßig wird nur "CM5"
angezeigt, wenn erkannt wird, dass sie unter Linux läuft (dem eigenen OS
des echten CM5), und "alles anzeigen" unter Windows/macOS.

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
Checking GitHub... 44/44
PROJECT                        STACK       LOCAL     GITHUB    STATE
--------------------------------------------------------------------
HYDRA-UMC                      firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER               node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO               node        0.0.8     0.1.3     OUTDATED
...
44/44 installed, 2 outdated

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Pulled latest into /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER
OK  build.sh completed successfully.
```

`hydra-umc-updater` ohne Argumente aufzurufen (oder per Doppelklick)
öffnet dieselbe Information in einem Fenster - eine Projekttabelle, ein
Filter nach Deployment-Ziel, und Installieren/Aktualisieren-Schaltflächen
für die ausgewählte Zeile.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="Echte HYDRA-UMC-UPDATER Desktop-Ubersicht" width="100%">
</p>

## 2. 🔄 WIE EINE PRÜFUNG/AKTUALISIERUNG WIRKLICH FUNKTIONIERT

- **Versionsquelle**: Die "Kilometerzähler"-Auto-Inkrement-Konvention
  dieses Ökosystems (jeder echte Build erhöht eine Versionsnummer, die
  IN einer Quelldatei lebt - `pyproject.toml`, `Cargo.toml`,
  `version.go`, `package.json`, `version.properties`, `pubspec.yaml`
  oder ein Firmware-`#define`, je nach Stack des Projekts) hat nie einen
  Git-Tag oder ein GitHub-Release für diesen Sprung erzeugt. Dieses Tool
  liest daher DIESELBE Datei, die das eigene `bump_version.py`/
  Build-Skript jedes Projekts bereits schreibt, direkt vom
  Standard-Branch des Repos über GitHubs Raw-Content-Host - nicht die
  Releases-API, die melden würde, dass alle Projekte keinerlei Releases
  haben.
- **Lokale Erkennung**: Für jedes der 44 bekannten Projekte wird
  geprüft, ob ein Verzeichnis mit genau diesem Namen unter der
  Workspace-Wurzel existiert (das Standard-Layout des Ökosystems - jedes
  Projekt als Geschwisterverzeichnis, genau das, was build-frontend.sh/
  HYDRA-UMC-SUITEs eigene Discovery bereits voraussetzen), und falls ja,
  wird dessen eigene lokale Kopie derselben Versionsdatei gelesen.
- **Eine einzige Parsing-Implementierung** (`version_parse.py`) wird
  zwischen dem lokalen Lesen und dem GitHub-Abruf geteilt, sodass ein
  lokaler Checkout und ein GitHub-Abruf niemals von zwei unabhängig
  auseinanderdriftenden Regexes interpretiert werden.
- **Installieren/Aktualisieren**: `git clone` (Installation) oder `git
  pull --ff-only` (Aktualisierung - nie ein erzwungener Reset, sodass
  echte lokale Änderungen laut fehlschlagen statt verworfen zu werden),
  dann wird das eigene `build.sh`/`build.bat` dieses Projekts (oder ein
  bekanntes Äquivalent - siehe Abschnitt 3) ausgeführt. Dieses Tool
  reimplementiert nie die eigenen Build-Schritte eines Projekts - siehe
  Abschnitt 3 für das Warum.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Echte HYDRA-UMC-UPDATER Checkpoints wahrend Installation oder Aktualisierung" width="100%">
</p>

## 3. 🧱 ARCHITEKTUR UND DESIGN-ENTSCHEIDUNGEN

- **Qt-Quick-GUI standardmäßig, `--cli` für Headless.** `main.py` prüft
  `--cli`, bevor die optionale PySide6-Laufzeit importiert wird. Die CLI
  funktioniert auf einer CM5 ohne Display und Desktop-Abhangigkeit; ohne
  Argumente startet QML, sofern verfugbar, und Tkinter bleibt nur Fallback.
- **`deploy` ist eine Klassifizierung, keine Einschränkung.** Alle 44
  Projekte als "Dinge, die auf den CM5 gehören" zu behandeln, war falsch
  - Firmware-Repos werden VON einem PC kompiliert und geflasht (der CM5
  braucht nur die resultierende Binärdatei über CAN-OTA, nie den
  eigenen Quellcode dieses Repos), und mehrere Werkzeuge (URTC-FLASHER,
  HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...) sollen auf dem eigenen
  Arbeitsplatz eines Bedieners laufen, nicht innerhalb der Zelle selbst.
  Das `deploy`-Feld von `registry.py` ("cm5" / "user-pc" / "mobile" /
  "wearable") verzeichnet das, und der GUI-Filter verwendet es als
  sinnvollen Ausgangspunkt - nie als harte Einschränkung, da dieses
  selbe Tool auch auf dem eigenen PC eines Entwicklers laufen soll, wo
  alle 44 gleichermaßen zulässig zu inspizieren sind.
- **Keine stack-spezifische Build-Logik in diesem Tool.** Das Ökosystem
  umfasst 7 Toolchains (Python, Rust, Go, Node/TS, Android/Kotlin,
  Flutter, ARM-Firmware). `npm install && npm run build` / `cargo build
  --release` / `./gradlew assembleDebug` / usw. HIER
  zu reimplementieren würde einen zweiten Ort schaffen, der
  vorgibt zu wissen, wie jedes Projekt gebaut wird - garantiert vom
  echten (und bereits korrekten) `build.sh`/`.bat` dieses Projekts
  abzudriften. `install.py` sucht stattdessen nach einem bekannten
  Build-Skript-Namen (`build.sh`, `build_firmware.sh`, `build_exe.sh`,
  `build-android.sh` und ihren `.bat`-Äquivalenten - die realen Namen,
  die über die 44 Projekte hinweg verwendet werden) und führt aus, was
  existiert.
- **GitHub-Rohinhalt, nicht die Releases-API.** Siehe Abschnitt 2 oben -
  die Versionierungskonvention dieses Ökosystems erzeugt nie ein
  Tag/Release, daher wäre die Releases-API hier aktiv falsch, nicht nur
  weniger bequem.
- **Ein vorübergehender Netzwerkfehler bekommt einen echten
  Wiederholungsversuch; eine definitive Antwort nie.** Jede echte
  GitHub-Anfrage (`_urlopen_with_retries` in `github_client.py`)
  wiederholt bis zu 3-mal mit Backoff, aber nur, wenn die Verbindung
  überhaupt keine Antwort erhalten hat (DNS/Timeout/Reset). Ein echter
  HTTP-Status, den GitHub tatsächlich zurückgegeben hat - 404, 403, 500 -
  wird nie wiederholt: GitHub hat bereits geantwortet, und ein erneuter
  Versuch würde nur mehr Rate-Limit für dasselbe Ergebnis verbrauchen.
- **Ein fehlerhafter entfernter Katalog schlägt laut fehl; ein
  fehlerhaftes Projekt nicht.** Wenn die GitHub-Repository-Liste selbst
  nicht erreichbar oder nicht parsbar ist, löst `discover_remote_projects()`
  eine Ausnahme aus - sowohl `gui.py` als auch `main.py` fangen sie
  bereits ab und fallen auf die lokal entdeckte Projektliste zurück,
  statt einen defekten oder leeren Scan anzuzeigen. Das fehlerhafte
  Manifest eines einzelnen Repositorys wird dagegen in die eigene
  `errors`-Liste dieses Scans isoliert und bricht die Entdeckung des
  restlichen Katalogs nie ab - ein echter Test mit Fixture-Server
  (`tests/test_github_client.py`) belegt beide Pfade.
- **`install`/`update` erwarten immer einen expliziten Projektnamen.**
  Es gibt keinen "alles aktualisieren"-Unterbefehl, und das ist eine
  Design-Entscheidung, kein fehlendes Feature - eine Flotte echter
  Roboter ist nichts, das man unbeaufsichtigt sich selbst aktualisieren
  lässt. `status` zeigt, was veraltet ist; ein Mensch wählt, welches
  Projekt wirklich angefasst wird.
- **Nur Standardbibliothek.** `urllib` für die GitHub-Abrufe
  (`github_client.py`), `subprocess` für git-/Build-Skript-Aufrufe
  (`install.py`), sonst nichts - dass ein Tool, das für die
  Abhängigkeits-Gesundheit ALLER anderen Projekte verantwortlich ist,
  selbst ohne Abhängigkeiten bleibt, ist bewusst.
- **Bekannte Vereinfachung**: HYDRA-UMC und URTC sind echte
  Mehrkomponenten-Firmware-Repos (6 bzw. 4 unabhängig versionierte
  Binärdateien - siehe deren eigene `VERSION_CHECKLIST.txt`/
  `build_firmware.sh`) ohne eine einzige "die" Versionsnummer.
  `registry.py` verfolgt EINE repräsentative Komponente pro Repo - genug,
  um "ist dieses Repo ungefähr aktuell?" zu beantworten, kein Ersatz für
  `build_firmware.sh`s eigene `firmware_manifest.json` für ein echtes
  Flashen.

## 📂 VERZEICHNISSTRUKTUR

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py        # Die 44 Projekte: Repo, Stack, Versionsdatei, Muster, Deployment-Ziel
│   ├── version_parse.py   # EINE Regex-Extraktions-Implementierung, lokal+GitHub
│   ├── detect.py          # Scannt eine Workspace-Wurzel nach Installiertem
│   ├── github_client.py   # Nebenläufiger Abruf des Rohinhalts + echter Wiederholungsversuch/Backoff bei vorübergehenden Netzwerkfehlern
│   ├── install.py         # git clone/pull + delegiert an das eigene Build-Skript
│   ├── qt_gui.py           # Qt-Quick-Bruecke zu realen Erkennungs-/Update-Diensten
│   ├── qml/Main.qml        # Desktop-Shell mit Theme, Checkpoints und About
│   ├── gui.py              # Tkinter-Fallback falls PySide6 nicht verfugbar ist
│   └── main.py             # Dispatch: GUI standardmäßig, --cli für status/install/update
├── build.sh / build.bat    # venv + editierbare Installation + Compile-Check
├── run.sh / run.bat        # Standard-GUI / CLI-Einstieg
├── run-gui.vbs             # Windows-GUI-Starter ohne Konsole
└── bump_version.py         # Ökosystemweiter "Kilometerzähler"-Sprung (pyproject.toml + __init__.py)
```

## ⚙️ BUILD UND AUSFÜHRUNG

```bash
chmod +x build.sh   # einmalig
./build.sh          # erstellt .venv, pip install -e ., Compile-Check von allem
./run.sh                              # Fenster-GUI (standardmäßig)
./run.sh --cli status                 # was installiert ist, lokale vs. GitHub-Version
./run.sh --cli status --offline       # dasselbe, ohne GitHub-Prüfung
./run.sh --cli install <PROJEKT-NAME> # klont + baut ein noch nicht installiertes Projekt
./run.sh --cli update  <PROJEKT-NAME> # aktualisiert + baut ein bereits installiertes Projekt neu
```

Unter Windows: `build.bat`, dann `run.bat` (GUI) / `run.bat --cli status`
/ `run.bat --cli install <Name>` / `run.bat --cli update <Name>`.

Die bevorzugte GUI braucht die optionale Qt-Laufzeit (`pip install -e ".[gui]"`;
`build.bat`/`build.sh` installieren sie bereits). `--cli` hat keine GUI-
Abhangigkeit und ist der richtige Einstieg fuer eine headless CM5. Ohne Qt
bleibt das alte Tkinter-Fenster nur ein Kompatibilitats-Fallback.

**Fehlerbehebung**

- `status` zeigt `?` für die lokale oder GitHub-Version eines Projekts:
  Dessen Versionsdatei existiert, aber die Konvention dieses Projekts hat
  sich seit der letzten Aktualisierung von `registry.py` geändert -
  prüfen Sie den Eintrag dieses Projekts in `registry.py` gegen dessen
  echte, aktuelle Versionsdatei.
- `status` zeigt `-` für GitHub ohne angezeigten Fehler: führen Sie
  `status` aus (ohne `--offline`) - `-` erscheint nur, wenn die
  GitHub-Prüfung komplett übersprungen wurde.
- `install`/`update` schlägt fehl mit "No build.sh/.bat found": Dieses
  Projekt verwendet einen Build-Skript-Namen, den dieses Tool noch nicht
  kennt - prüfen Sie dessen eigenes README für den echten Namen und
  erwägen Sie, ihn zu den eigenen `BUILD_SCRIPT_CANDIDATES_*`-Listen von
  `install.py` hinzuzufügen.
- `git pull --ff-only` schlägt fehl: Der lokale Checkout hat nicht
  committete Änderungen oder die Historie ist auseinandergelaufen -
  lösen Sie das manuell (`git status` im eigenen Verzeichnis des
  Projekts), bevor Sie `update` erneut versuchen. Dieses Tool erzwingt
  nie einen Reset eines Checkouts.

## 🚀 ROADMAP

- Eine gepackte eigenständige GUI-ausführbare Datei (PyInstaller, nach der
  eigenen `build_exe.bat`/`.sh`-Konvention von HYDRA-UMC-SUITE) für eine
  Doppelklick-Installation ganz ohne `pip`/venv-Schritt - heute braucht
  die GUI noch vorher `./build.sh`, genau wie die CLI.
- Optionale Abhängigkeits-Vorprüfung pro Projekt (fehlende Toolchains
  melden - kein Rust/Go/Android-SDK/Flutter installiert - bevor ein
  `install` mittendrin fehlschlägt).
- Ein `--json`-Ausgabemodus für `status`, um es skriptbar zu machen.
- Komponentenweise Nachverfolgung für die eigene Mehrbinär-Firmware von
  HYDRA-UMC/URTC (siehe die "bekannte Vereinfachung" in Abschnitt 3),
  sobald ein echter Bedarf über die heute verfolgte einzelne
  repräsentative Komponente hinaus besteht.

## 🔗 VERWANDTE PROJEKTE

Der gesamte Zweck dieses Tools ist die Verwaltung jedes anderen Projekts
im Ökosystem - statt alle 44 hier aufzulisten (siehe `registry.py` für
die exakte, maßgebliche Liste), die zwei rollenmäßig nächsten:

- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - der
  Flaggschiff-Multi-Roboter-Zellencontroller, den dieses Tool auf der
  echten CM5-Hardware installiert und aktuell halten soll.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** -
  ein weiteres eigenständiges Python-Tool, das neben dem
  Zellencontroller laufen soll, rollenmäßig der nächste Verwandte (ein
  fokussiertes Dienstprogramm auf der CM5-Seite, nicht Teil des
  Robotersteuerungspfads selbst).

**Rest des Ökosystems** (jedes Projekt, das dieses Tool erkennen/
installieren/aktualisieren kann): die 12 ursprünglichen Projekte
(Firmware, Server, Mobile/Desktop-Apps), die Vision/Cognitive-KI-Knoten,
die Orchestrierungs-/Simulationsdienste in Rust, die
Infrastruktur-/CLI-Tools in Go, die Industrie-Gateways in Node, und die
Werkzeugkopf-Firmware/PC-Tools von URTC - siehe die eigene Gruppierung
in `registry.py` (die den Verzeichnisstruktur-Kommentaren dieses selben
READMEs entspricht) für die vollständige, aktuelle Liste.

## 👤 AUTOR

**JuanenRac (Electro Hobby 3D)**
E-Mail: electrohobby3d@gmail.com
YouTube: [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

GPL-3.0 (Software) / CC BY-SA 4.0 (Dokumentation) - siehe [LICENSE.md](LICENSE.md).
