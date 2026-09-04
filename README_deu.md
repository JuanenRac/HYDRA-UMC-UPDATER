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

> **Visueller Desktopmodus:** die Standard-Desktopoberfläche nutzt jetzt
> **Qt Quick / QML** mit der optionalen GUI-Laufzeit `PySide6`. Kern und
> `--cli` bleiben für eine headless CM5 reine Standardbibliothek.
>
> **Windows-Start und Nachweise:** öffnen Sie `run-gui.vbs` (oder `run.bat`
> ohne Argumente) für den konsolenfreien Desktop-Client. Das Update-Panel zeigt
> echte Checkpoints für Vorabprüfung, Quelle, Manifest, Build-test und Abschluss
> mit erfassten Nachweisen; `run.bat --cli ...` behält das Diagnose-Terminal.
> Installieren ist nur ohne Checkout aktiv, Aktualisieren nur bei neuerer
> GitHub-Version. Während einer bestätigten Aktion ersetzen Checkpoints die
> Projektsteuerung; eine neue Projektauswahl stellt sie wieder her.
> **Alle fehlenden installieren** und **Alle veralteten aktualisieren** sind
> separat bestätigte, sequenzielle Sammelaktionen auf Basis desselben realen
> Zustands und Sicherheitswegs.

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

HYDRA-UMC-UPDATER ist ein kleines Tool - Fenster-GUI standardmäßig, volle
CLI mit `--cli` - das sowohl auf dem echten CM5 als auch auf dem eigenen
Windows/Linux/macOS-Rechner eines Entwicklers laufen soll (jeder
Workspace mit demselben Checkout-Layout) und drei Fragen für jedes der
anderen 55 Ökosystem-Projekte beantwortet:

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

Auch gehören nicht alle 55 Projekte auf den CM5 - die meisten
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
Checking GitHub... 55/55
PROJECT                        STACK       LOCAL     GITHUB    STATE
--------------------------------------------------------------------
HYDRA-UMC                      firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER               node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO               node        0.0.8     0.1.3     OUTDATED
...
55/55 installed, 2 outdated

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
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="Echte HYDRA-UMC-UPDATER Desktop-Übersicht" width="100%">
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
- **Lokale Erkennung**: Für jedes der 55 bekannten Projekte wird
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
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Echte HYDRA-UMC-UPDATER Checkpoints während Installation oder Aktualisierung" width="100%">
</p>

## 3. 🧱 ARCHITEKTUR UND DESIGN-ENTSCHEIDUNGEN

- **Qt-Quick-GUI standardmäßig, `--cli` für Headless.** `main.py` prüft
  `--cli`, bevor die optionale PySide6-Laufzeit importiert wird. Die CLI
  funktioniert auf einer CM5 ohne Display und Desktop-Abhängigkeit; ohne
  Argumente startet QML, sofern verfügbar, und Tkinter bleibt nur Fallback.
- **Die Fenster-GUI ist echt und mehrsprachig in 7 Sprachen (`i18n.py`) - `--cli` ist es absichtlich nicht.** Jedes echte Widget benennt sich live aus einer Sprach-`Combobox` neu (en/es/fr/it/de/zh/ja, dieselben 7, die das öffentliche Dashboard und jede README ausliefern), erkannt aus einer gespeicherten Präferenz oder dem eigenen Locale des Betriebssystems. Projekt-/Familiennamen sowie der echte `notes`/`tech`-Text jedes Projekts bleiben unübersetzt - `registry.py` ist ihre einzige Quelle der Wahrheit, und 7 parallele Kopien echter Engineering-Dokumentation würden genau das verhindern. Die `--cli`-Ausgabe bleibt absichtlich nur auf Englisch: Sie ist zum Skripten/Weiterleiten gedacht, wo stabiler, grep-barer Text mehr zählt als Lokalisierung.
- **`deploy` ist eine Klassifizierung, keine Einschränkung.** Alle 55
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
  alle 55 gleichermaßen zulässig zu inspizieren sind.
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
  die über die 55 Projekte hinweg verwendet werden) und führt aus, was
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
│   ├── registry.py         # ProjectEntry - kein statischer Katalog; wird zur Erkennungszeit aus dem eigenen Manifest jedes Repos gebaut
│   ├── project_manifest.py # Liest/validiert eine repository-eigene hydra-umc.project.json
│   ├── ecosystem_catalog.py # Parser für den öffentlichen JuanenRac-Ökosystem-Erkennungskatalog
│   ├── version_parse.py   # EINE Regex-Extraktions-Implementierung, lokal+GitHub
│   ├── detect.py          # Scannt eine Workspace-Wurzel nach Installiertem
│   ├── github_client.py   # Nebenläufiger Abruf des Rohinhalts + echter Wiederholungsversuch/Backoff bei vorübergehenden Netzwerkfehlern
│   ├── install.py         # git clone/pull + delegiert an das eigene Build-Skript
│   ├── i18n.py             # Echte, vollständige GUI-Übersetzungen (7 Sprachen)
│   ├── qt_gui.py           # Qt-Quick-Brücke zu realen Erkennungs-/Update-Diensten
│   ├── qml/Main.qml        # Desktop-Shell mit Theme, Checkpoints und About
│   ├── gui.py              # Tkinter-Fallback falls PySide6 nicht verfügbar ist
│   └── main.py             # Dispatch: GUI standardmäßig, --cli für status/install/update
├── tests/                  # Echte Tests: github_client, i18n, install, project_manifest, registry
├── docs/
│   ├── CLI_REFERENCE.md     # Befehlsreferenz
│   └── QML_DESKTOP_GUI.md   # Qt-Quick-GUI-Architektur
├── images/                 # Medien, App-Icons und Interface-Screenshots
├── tools/
│   ├── build_test.py        # Nicht-versionierender Build-Check
│   ├── ci_validate.py       # Manifest/CHANGELOG/Docs-Validierung, von CI genutzt
│   ├── generate_app_icon.py # Rendert das öffentliche HYDRA-UMC-SVG in das von Windows genutzte Icon
│   ├── migrate_project_manifests.py  # Prüft einen Workspace nach der einmaligen Manifest-Migration
│   └── validate_project_manifests.py # Validiert repository-eigene Manifeste + native Build-Versionen
├── .env.example            # Umgebungsvariablen-Vorlage
├── build.sh / build.bat    # venv + editierbare Installation + Compile-Check
├── run.sh / run.bat        # Standard-GUI / CLI-Einstieg
├── run-gui.vbs             # Windows-GUI-Starter ohne Konsole
├── bump_version.py         # Ökosystemweiter "Kilometerzähler"-Sprung (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
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
Abhängigkeit und ist der richtige Einstieg für eine headless CM5. Ohne Qt
bleibt das alte Tkinter-Fenster nur ein Kompatibilitäts-Fallback.

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

## 🚀 FAHRPLAN

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

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Direkt verwandt**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das physische Motherboard des Roboterarms: CM5-Host + Dual-Core-STM32H745, koordiniert bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA — der Flaggschiff-Multi-Roboter-Zellcontroller, den dieses Tool auf der echten CM5-Hardware installiert und aktuell halten soll.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (PySide6) für mehrere Server gleichzeitig, verpackt als eigenständige ausführbare Datei — ein weiteres eigenständiges Python-Tool, das neben dem Zellcontroller laufen soll, der rollentechnisch nächste Verwandte (ein fokussiertes CM5-seitiges Dienstprogramm, nicht Teil des eigentlichen Robotersteuerungspfads).
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — hängt beim Bau eines neuen CM5-Images von diesem Projekt als echter Bibliothek für die eigene GitHub-Ökosystem-Erkennung ab, statt einer zweiten, unabhängig driftenden Implementierung.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Sicherheitsschranke, gegen die jede Bridge ihre Befehle validiert.

*Kern-Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit echtem GRBL-Status-/Steuerbyte-Zugriff.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, liest 3 echte Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Sicherungen.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, träge importierten rclpy-ROS-2-Transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem echten MAVLink-Befehlssender.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes Position-Based-Visual-Servoing-Korrekturgesetz, sicherheitsgesteuert nach vorgelagertem Zonenstatus.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und E-STOP-Anforderung, mit erzwungener Kalibrierungsaktualität.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echte Hardware-in-the-Loop-Sicherheitsverriegelung, die Befehle zwischen Simulation und echter Hardware routet.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrationsknoten, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe.

*Ergänzende Tools & Ökosystembetrieb*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.

---

## 📚 Dokumentation & Community

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — jeder `--cli`-Unterbefehl, echte Ausgabe aus einem echten installierten Lauf, und der Exit-Code-Vertrag.
- **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — wie der Qt Quick/QML-Desktop-Client aufgebaut ist, und wie er eine echte Kontrolloberfläche über demselben Backend bleibt, das auch `--cli` verwendet, statt einer zweiten Implementierung.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

GPL-3.0 (Software) / CC BY-SA 4.0 (Dokumentation) - siehe [LICENSE.md](LICENSE.md).
