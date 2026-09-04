<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | 🇮🇹 <b>Italiano</b> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📦 Rileva, installa e aggiorna manualmente l'intero ecosistema HYDRA-UMC/URTC

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only CLI core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
</p>

> **Modalità desktop visiva:** l'interfaccia desktop predefinita usa ora
> **Qt Quick / QML** con il runtime GUI opzionale `PySide6`. Il nucleo e
> `--cli` restano solo libreria standard per una CM5 senza schermo.
>
> **Avvio Windows ed evidenze:** apri `run-gui.vbs` (o `run.bat` senza
> argomenti) per il client grafico senza console. Il pannello di aggiornamento
> mostra checkpoint reali di preflight, sorgente, manifest, build-test e fine
> con evidenze catturate; `run.bat --cli ...` conserva il terminale diagnostico.
> Installa è attivo solo senza checkout e Aggiorna solo se GitHub è più recente.
> Durante un'azione approvata i checkpoint sostituiscono i controlli del
> progetto; selezionare un altro progetto li ripristina.
> **Installa tutti i mancanti** e **Aggiorna tutti gli obsoleti** sono azioni
> in blocco sequenziali, confermate separatamente e basate sullo stesso stato
> reale e percorso di sicurezza.

---

## 1. 🛠️ PANORAMICA TECNICA

HYDRA-UMC-UPDATER è un piccolo strumento - GUI con finestra per
impostazione predefinita, CLI completa con `--cli` - pensato per girare
sia sul vero CM5 sia sulla macchina Windows/Linux/macOS personale di uno
sviluppatore (qualsiasi workspace con lo stesso tipo di checkout) che
risponde a tre domande per ciascuno degli altri 54 progetti
dell'ecosistema:

1. **Cosa c'è realmente installato qui, e in quale versione?**
2. **Qual è l'ultima versione pubblicata su GitHub?**
3. **Se GitHub ha una versione più recente, fammi aggiornare QUEL progetto, a mano.**

Quest'ultimo punto è deliberato e non negoziabile: questo strumento non
aggiorna mai più di un progetto per comando, e mai di propria iniziativa.
Una cella di controllo robot non è qualcosa che si vuole veder
aggiornarsi da sola di notte - ogni aggiornamento reale è un comando (o
un clic su un pulsante, per una riga selezionata nella tabella della
GUI) innescato da una persona, per un progetto con un nome, di cui può
vedere il risultato prima di toccare il successivo.

Nemmeno tutti e 54 i progetti appartengono al CM5 - la maggior parte dei
repository con prefisso URTC e alcuni di HYDRA-UMC sono strumenti che uno
sviluppatore esegue dal proprio PC (il firmware viene compilato e
flashato DAL posto di lavoro, non costruito SULLA cella), oppure app
installate su un telefono/orologio. Il proprio campo `deploy` di
`registry.py` registra quale è quale (vedi sezione 3), e la tabella dei
progetti della GUI filtra su di esso - per impostazione predefinita
mostra "solo CM5" quando rileva di girare su Linux (il proprio SO del
vero CM5), e "mostra tutto" su Windows/macOS.

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
Checking GitHub... 54/54
PROJECT                        STACK       LOCAL     GITHUB    STATE
--------------------------------------------------------------------
HYDRA-UMC                      firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER               node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO               node        0.0.8     0.1.3     OUTDATED
...
54/54 installed, 2 outdated

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Pulled latest into /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER
OK  build.sh completed successfully.
```

Avviare `hydra-umc-updater` senza argomenti (o con doppio clic) apre la
stessa informazione in una finestra - una tabella di progetti, un filtro
per obiettivo di distribuzione, e pulsanti Installa/Aggiorna per la riga
selezionata.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="Panoramica reale desktop di HYDRA-UMC-UPDATER" width="100%">
</p>

## 2. 🔄 COME FUNZIONA DAVVERO UN CONTROLLO/AGGIORNAMENTO

- **Origine della versione**: la convenzione "contachilometri" di
  auto-incremento di questo ecosistema (ogni build reale incrementa un
  numero di versione che vive DENTRO un file sorgente - `pyproject.toml`,
  `Cargo.toml`, `version.go`, `package.json`, `version.properties`,
  `pubspec.yaml`, o un `#define` di firmware, a seconda dello stack del
  progetto) non ha mai creato un tag git né una GitHub Release per
  quell'incremento. Questo strumento legge quindi lo STESSO file che il
  proprio `bump_version.py`/script di build di ogni progetto già scrive,
  direttamente dal branch predefinito del repo tramite l'host di
  contenuto raw di GitHub - non l'API delle Releases, che riporterebbe
  che tutti i progetti non hanno alcuna release.
- **Rilevamento locale**: per ciascuno dei 54 progetti conosciuti,
  controlla se esiste una directory con quel nome esatto sotto la radice
  del workspace (la disposizione standard dell'ecosistema - ogni
  progetto come directory sorella, esattamente ciò che già presuppongono
  build-frontend.sh e il proprio discovery di HYDRA-UMC-SUITE), e se sì,
  legge la propria copia locale di quello stesso file di versione.
- **Un'unica implementazione di parsing** (`version_parse.py`) è
  condivisa tra la lettura locale e il recupero da GitHub, così un
  checkout locale e un recupero da GitHub non vengono mai interpretati
  da due regex che potrebbero divergere indipendentemente.
- **Installare/aggiornare**: `git clone` (installazione) o `git pull
  --ff-only` (aggiornamento - mai un reset forzato, così vere modifiche
  locali falliscono rumorosamente invece di essere scartate), poi esegue
  il `build.sh`/`build.bat` proprio di quel progetto (o un equivalente
  noto - vedi sezione 3). Questo strumento non reimplementa mai i passi
  di build propri di un progetto - vedi sezione 3 per il perché.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Checkpoint reali durante installazione o aggiornamento di HYDRA-UMC-UPDATER" width="100%">
</p>

## 3. 🧱 ARCHITETTURA E DECISIONI DI DESIGN

- **GUI Qt Quick predefinita, `--cli` per headless.** `main.py` controlla
  `--cli` prima di importare il runtime PySide6 opzionale. La CLI funziona su
  una CM5 senza schermo né dipendenze desktop; senza argomenti avvia QML quando
  disponibile e Tkinter resta solo un fallback temporaneo.
- **La GUI con finestra è reale, multilingue in 7 lingue (`i18n.py`) - `--cli` deliberatamente non lo è.** Ogni widget reale si ri-etichetta dal vivo da una `Combobox` di lingua (en/es/fr/it/de/zh/ja, le stesse 7 pubblicate dalla dashboard pubblica e da ogni README), rilevata da una preferenza salvata o dalla locale propria del sistema operativo. I nomi di progetti/famiglie e il testo reale `notes`/`tech` di ciascun progetto restano non tradotti - `registry.py` è la loro unica fonte di verità, e 7 copie parallele di documentazione ingegneristica reale impedirebbero che lo restasse. L'output di `--cli` resta volutamente solo in inglese: è pensato per essere scriptato/reindirizzato, dove un testo stabile e grep-abile conta più della localizzazione.
- **`deploy` è una classificazione, non una restrizione.** Trattare tutti
  e 54 i progetti come "cose che appartengono al CM5" era sbagliato - i
  repository di firmware vengono compilati e flashati DA un PC (il CM5
  ha bisogno solo del binario risultante via CAN-OTA, mai del codice
  sorgente di questo repository), e diversi strumenti (URTC-FLASHER,
  HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...) sono pensati per girare sul
  proprio posto di lavoro di un operatore, non dentro la cella stessa.
  Il campo `deploy` di `registry.py` ("cm5" / "user-pc" / "mobile" /
  "wearable") registra questo, e il filtro della GUI lo usa come punto di
  partenza ragionevole - mai come restrizione rigida, dato che questo
  stesso strumento è anche pensato per girare sul PC personale di uno
  sviluppatore, dove tutti e 54 sono ugualmente validi da ispezionare.
- **Nessuna logica di build per stack in questo strumento.**
  L'ecosistema copre 7 toolchain (Python, Rust, Go, Node/TS,
  Android/Kotlin, Flutter, firmware ARM). Reimplementare `npm install &&
  npm run build` / `cargo build --release` / `./gradlew assembleDebug` /
  ecc. QUI creerebbe un secondo posto che pretende di sapere come
  compilare ogni progetto, garantito a divergere dal `build.sh`/`.bat`
  reale (e già corretto) di quel progetto. `install.py` invece cerca un
  nome di script di build conosciuto (`build.sh`, `build_firmware.sh`,
  `build_exe.sh`, `build-android.sh`, e i loro equivalenti `.bat` - i
  nomi reali usati nei 54 progetti) ed esegue quello che esiste.
- **Contenuto raw di GitHub, non l'API delle Releases.** Vedi la sezione
  2 - la convenzione di versionamento di questo ecosistema non crea mai
  un tag/release, quindi l'API delle Releases sarebbe attivamente
  sbagliata qui, non solo meno comoda.
- **Un errore di rete transitorio riceve un vero ritentativo; una
  risposta definitiva mai.** Ogni richiesta reale a GitHub
  (`_urlopen_with_retries` di `github_client.py`) riprova fino a 3 volte
  con backoff, ma solo quando la connessione non ha mai ottenuto alcuna
  risposta (DNS/timeout/reset). Uno stato HTTP reale che GitHub ha
  effettivamente restituito - 404, 403, 500 - non viene mai riprovato:
  GitHub ha già risposto, e insistere consumerebbe solo altro rate limit
  per lo stesso risultato.
- **Un catalogo remoto malformato fallisce rumorosamente; un singolo
  progetto malformato no.** Se l'elenco stesso dei repository GitHub è
  irraggiungibile o non analizzabile, `discover_remote_projects()`
  solleva un'eccezione - sia `gui.py` che `main.py` la catturano già e
  ricadono sull'elenco dei progetti scoperti localmente invece di
  mostrare una scansione rotta o vuota. Il manifest malformato di un
  singolo repository, invece, viene isolato nella lista `errors` di
  quella scansione e non interrompe mai la scoperta del resto - un vero
  test con server di fixture (`tests/test_github_client.py`) dimostra
  entrambi i percorsi.
- **`install`/`update` richiedono sempre il nome esplicito di un
  progetto.** Non esiste un sottocomando "aggiorna tutto", ed è una
  decisione di design, non una funzionalità mancante - una flotta di
  robot reali non è qualcosa che si lascia aggiornare da sola senza
  supervisione. `status` mostra cosa è obsoleto; una persona sceglie
  quale toccare davvero.
- **Solo libreria standard.** `urllib` per i recuperi da GitHub
  (`github_client.py`), `subprocess` per le chiamate a git/script di
  build (`install.py`), nient'altro - che uno strumento responsabile di
  mantenere sane le dipendenze di TUTTI gli altri progetti resti esso
  stesso senza dipendenze è deliberato.
- **Semplificazione nota**: HYDRA-UMC e URTC sono veri repo di firmware
  multi-componente (6 e 4 binari versionati in modo indipendente
  ciascuno - vedi il proprio `VERSION_CHECKLIST.txt`/`build_firmware.sh`)
  senza un unico numero di versione. `registry.py` segue UN componente
  rappresentativo per repo - sufficiente per rispondere "questo repo è
  più o meno aggiornato?", non un sostituto del proprio
  `firmware_manifest.json` di `build_firmware.sh` per un flash reale.

## 📂 STRUTTURA DELLE DIRECTORY

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py         # ProjectEntry - nessun catalogo statico; costruito a tempo di scoperta dal manifesto proprio di ogni repo
│   ├── project_manifest.py # Legge/valida un hydra-umc.project.json proprio del repository
│   ├── ecosystem_catalog.py # Parser del catalogo pubblico di scoperta dell'ecosistema di JuanenRac
│   ├── version_parse.py   # UN'implementazione di estrazione regex, locale+GitHub
│   ├── detect.py          # Scansiona una radice di workspace per ciò che è installato
│   ├── github_client.py   # Recupero concorrente del contenuto raw + ritentativo/backoff reale per errori di rete transitori
│   ├── install.py         # git clone/pull + delega allo script di build proprio
│   ├── i18n.py             # Traduzioni reali e complete della GUI (7 lingue)
│   ├── qt_gui.py           # Bridge Qt Quick verso i servizi reali di scoperta/aggiornamento
│   ├── qml/Main.qml        # Shell desktop a tema con checkpoint e About
│   ├── gui.py              # Fallback Tkinter se PySide6 non è disponibile
│   └── main.py             # Dispatch: GUI predefinita, --cli per status/install/update
├── tests/                  # Test reali: github_client, i18n, install, project_manifest, registry
├── docs/
│   ├── CLI_REFERENCE.md     # Riferimento comandi
│   └── QML_DESKTOP_GUI.md   # Architettura della GUI Qt Quick
├── images/                 # Media, icone dell'app e screenshot dell'interfaccia
├── tools/
│   ├── build_test.py        # Controllo build senza versionamento
│   ├── ci_validate.py       # Validazione manifest/CHANGELOG/docs usata dalla CI
│   ├── generate_app_icon.py # Renderizza l'SVG pubblico di HYDRA-UMC nell'icona usata da Windows
│   ├── migrate_project_manifests.py  # Verifica un workspace dopo la migrazione una tantum dei manifesti
│   └── validate_project_manifests.py # Valida i manifesti propri dei repo + le versioni native di build
├── .env.example            # Modello delle variabili d'ambiente
├── build.sh / build.bat    # venv + installazione editabile + compile-check
├── run.sh / run.bat        # GUI predefinita / ingresso CLI
├── run-gui.vbs             # Launcher grafico Windows senza console
├── bump_version.py         # Incremento "contachilometri" dell'ecosistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Sincronizza la versione di hydra-umc.project.json con quella nativa (--sync)
```

## ⚙️ COMPILAZIONE ED ESECUZIONE

```bash
chmod +x build.sh   # una tantum
./build.sh          # crea .venv, pip install -e ., compile-check di tutto
./run.sh                               # GUI con finestra (predefinita)
./run.sh --cli status                  # cosa è installato, versione locale vs. GitHub
./run.sh --cli status --offline        # lo stesso, senza controllare GitHub
./run.sh --cli install <NOME-PROGETTO> # clona + compila un progetto non ancora installato
./run.sh --cli update  <NOME-PROGETTO> # aggiorna + ricompila un progetto già installato
```

Su Windows: `build.bat`, poi `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli install <nome>` / `run.bat --cli update <nome>`.

La GUI preferita richiede il runtime Qt opzionale (`pip install -e ".[gui]"`;
`build.bat`/`build.sh` lo installano già). `--cli` non ha dipendenze GUI ed è
l'ingresso corretto per una CM5 headless. Senza Qt, la vecchia finestra
Tkinter resta solo un fallback di compatibilità.

**Risoluzione dei problemi**

- `status` mostra `?` per la versione locale o GitHub di un progetto: il
  suo file di versione esiste ma la convenzione di quel progetto è
  cambiata dall'ultimo aggiornamento di `registry.py` - controlla la
  voce di quel progetto in `registry.py` rispetto al suo file di
  versione reale attuale.
- `status` mostra `-` per GitHub senza alcun errore mostrato: esegui
  `status` (senza `--offline`) - `-` appare solo quando il controllo
  GitHub è stato saltato del tutto.
- `install`/`update` fallisce con "No build.sh/.bat found": quel
  progetto usa un nome di script di build che questo strumento non
  riconosce ancora - controlla il suo proprio README per quello reale, e
  valuta di aggiungerlo alle liste `BUILD_SCRIPT_CANDIDATES_*` proprie di
  `install.py`.
- `git pull --ff-only` fallisce: il checkout locale ha modifiche non
  committate o la cronologia è divergente - risolvilo manualmente (`git
  status` nella directory propria del progetto) prima di riprovare
  `update`. Questo strumento non forza mai un reset di un checkout.

## 🚀 TABELLA DI MARCIA

- Un eseguibile GUI autonomo pacchettizzato (PyInstaller, seguendo la
  propria convenzione `build_exe.bat`/`.sh` di HYDRA-UMC-SUITE) per
  un'installazione con doppio clic senza alcun passaggio `pip`/venv -
  oggi la GUI richiede ancora `./build.sh` prima, come la CLI.
- Controllo preliminare opzionale delle dipendenze per progetto
  (segnalare toolchain mancanti - nessun Rust/Go/SDK Android/Flutter
  installato - prima che un `install` fallisca a metà strada).
- Una modalità di output `--json` per `status`, per poterlo scriptare.
- Tracciamento per componente per il firmware multi-binario proprio di
  HYDRA-UMC/URTC (vedi la "semplificazione nota" nella sezione 3), non
  appena ci sarà una reale necessità oltre l'unico componente
  rappresentativo tracciato oggi.

## 🔗 Progetti Correlati

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerlo, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Direttamente Correlati**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la scheda madre fisica del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, che coordina fino a 8 bracci utensile via CAN-OTA/SPI-OTA — il controller di cella multi-robot di punta che questo strumento è pensato per mantenere installato e aggiornato sull'hardware CM5 reale.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando sciame desktop (PySide6) per più server contemporaneamente, pacchettizzato come eseguibile standalone — un altro strumento Python standalone pensato per essere eseguito accanto al controller di cella, il fratello più vicino per ruolo (un'utilità focalizzata lato CM5, non parte del percorso di controllo del robot stesso).
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — dipende da questo progetto come vera libreria per la propria scoperta dell'ecosistema su GitHub durante la costruzione di una nuova immagine della CM5, invece di una seconda implementazione che potrebbe divergere in modo indipendente.

**Fa Anche Parte dell'Ecosistema**

*Hardware e Piattaforma di Base*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — livello prodotto riproducibile su Raspberry Pi OS per il CM5: agente in sola lettura, config/profili validati, provisioning WiFi al primo contatto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto JSON-Schema condiviso e la barriera di sicurezza contro cui ogni bridge valida i propri comandi.

*Backend Centrale e Client*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il vero backend headless (REST/WebSocket) con cui parla davvero ogni client di controllo.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo web con visualizzazione 3D multi-robot in tempo reale.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo nativa per Android con login biometrico e un companion Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo per iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" a bordo, incorporata direttamente nel CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico desktop di URDF che invia i modelli finiti al catalogo di STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barriera di coordinamento per flotte AGV/AMR tramite un publisher MQTT VDA 5050 reale.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore ad alto livello per celle CNC con accesso reale a stato/byte di controllo GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barriera di coordinamento per droidi con zampe/umanoidi, con un vero mittente di comandi per Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore di sicurezza per celle laser che legge 3 salvaguardie GPIO reali di chiave/involucro/interblocco.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore ad alto livello sicuro per il flusso schede del pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barriera di coordinamento sicura per stampanti 3D Moonraker/Klipper, con comandi di lavoro reali e controllati.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore di sicurezza con un vero trasporto ROS 2 rclpy, importato in modo lazy.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barriera di coordinamento per UAV dotati di fotocamera, con un vero mittente di comandi MAVLink.

*Piattaforma Strumenti URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware per la scheda fisica dell'Universal Robot Tool Controller, oltre 25 profili utensile su bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — strumento desktop con GUI per il flashing delle schede URTC, CAN-OTA più SWD/JTAG a chip intero.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — strumento desktop di diagnostica CAN-bus dal vivo per schede URTC, un pannello per profilo utensile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa basata su browser a URTC-TESTER tramite la Web Serial API, senza installazione locale.

*Nodo IA Visione (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica di caricamento sicuro per architettura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + config MediaMTX, con una vera barriera di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vera legge di correzione Position-Based Visual Servoing, con cancello di sicurezza sullo stato di zona a monte.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vero controllo di violazione zona e richiesta E-STOP, con imposizione della freschezza di calibrazione.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay verso Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione dei task basata su regole e recupero semantico degli errori sui codici errore MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF (solo libreria standard) sui documenti Markdown di questo ecosistema.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e una macchina a stati di missione.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute della flotta basato su gRPC, con retry/backoff e rilevamento di discrepanza d'identità.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorsi 3D basato su RRT, con vera validazione delle collisioni ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, con property test per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub di integrazione per il motore di gemello digitale, con un vero contratto di sincronizzazione per compatibilità di versione.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vero interblocco di sicurezza hardware-in-the-loop che instrada i comandi tra simulazione e hardware reale.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vera cinematica diretta e validazione dei limiti articolari su un vero sottoinsieme URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vero generatore procedurale di scene 2D con esportazione di annotazioni YOLO/COCO.

*Dati e Analisi*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vero archivio di serie temporali basato su sqlite3, con una vera API HTTP di ingestione/query.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vero rilevatore di anomalie FFT + baseline statistica, con monitoraggio della deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vero calcolo OEE/disponibilità sullo storico di DATALAKE, con esportazione CSV riproducibile.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vera pipeline di ingestione CAN/WebSocket verso DATALAKE, con deduplicazione per sequenza.

*Gateway Industriale*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub di integrazione che inoltra ai protocolli industriali, con un vero livello di allowlist dei comandi/backpressure.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vero spazio di indirizzi OPC-UA, verificato con una vera sessione client del protocollo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vero broker MQTT con autenticazione opzionale per client e ACL sui topic.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — veri endpoint XML `/probe` e `/current` di MTConnect, con output in modalità degradata.

*Strumenti Complementari e Operazioni dell'Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — pannelli Smart Summaries e Anomaly Highlighting su DATALAKE/ANOMALY-DETECTOR, con un fallback statistico onesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI di flotta con un vero e stabile contratto di exit-code, un client live reale della stessa API di HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app companion WearOS con avvisi aptici reali e un relay vocale verso il telefono abbinato.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware per un rack di montaggio schede con decodifica reale dell'ID utensile e logica di preriscaldamento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware più un vero companion di visione Python per una testa utensile di ispezione termica/RGB.

---

## 📚 Documentazione e Comunità

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — ogni sottocomando `--cli`, output reale catturato da un'esecuzione reale installata, e il contratto dei codici di uscita.
- **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — come è strutturato il client desktop Qt Quick/QML, e come resta una vera superficie di controllo sullo stesso backend usato da `--cli`, non una seconda implementazione.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnologico e linee guida di codifica per una pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — gli standard di comportamento attesi in questa comunità.
- **[SECURITY.md](SECURITY.md)** — come segnalare una vulnerabilità, e le reali aree di attenzione sulla sicurezza di questo progetto.
- **[SUPPORT.md](SUPPORT.md)** — dove porre domande e segnalare bug.

## 👤 AUTORE
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENZA

GPL-3.0 (software) / CC BY-SA 4.0 (documentazione) - vedi [LICENSE.md](LICENSE.md).
