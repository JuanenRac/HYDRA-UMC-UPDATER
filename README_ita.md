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

> **Modalita desktop visiva:** l'interfaccia desktop predefinita usa ora
> **Qt Quick / QML** con il runtime GUI opzionale `PySide6`. Il nucleo e
> `--cli` restano solo libreria standard per una CM5 senza schermo.
>
> **Avvio Windows ed evidenze:** apri `run-gui.vbs` (o `run.bat` senza
> argomenti) per il client grafico senza console. Il pannello di aggiornamento
> mostra checkpoint reali di preflight, sorgente, manifest, build-test e fine
> con evidenze catturate; `run.bat --cli ...` conserva il terminale diagnostico.
> Installa e attivo solo senza checkout e Aggiorna solo se GitHub e piu recente.
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
risponde a tre domande per ciascuno degli altri 44 progetti
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

Nemmeno tutti e 44 i progetti appartengono al CM5 - la maggior parte dei
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
- **Rilevamento locale**: per ciascuno dei 44 progetti conosciuti,
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
  una CM5 senza schermo ne dipendenze desktop; senza argomenti avvia QML quando
  disponibile e Tkinter resta solo un fallback temporaneo.
- **`deploy` è una classificazione, non una restrizione.** Trattare tutti
  e 44 i progetti come "cose che appartengono al CM5" era sbagliato - i
  repository di firmware vengono compilati e flashati DA un PC (il CM5
  ha bisogno solo del binario risultante via CAN-OTA, mai del codice
  sorgente di questo repository), e diversi strumenti (URTC-FLASHER,
  HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...) sono pensati per girare sul
  proprio posto di lavoro di un operatore, non dentro la cella stessa.
  Il campo `deploy` di `registry.py` ("cm5" / "user-pc" / "mobile" /
  "wearable") registra questo, e il filtro della GUI lo usa come punto di
  partenza ragionevole - mai come restrizione rigida, dato che questo
  stesso strumento è anche pensato per girare sul PC personale di uno
  sviluppatore, dove tutti e 44 sono ugualmente validi da ispezionare.
- **Nessuna logica di build per stack in questo strumento.**
  L'ecosistema copre 7 toolchain (Python, Rust, Go, Node/TS,
  Android/Kotlin, Flutter, firmware ARM). Reimplementare `npm install &&
  npm run build` / `cargo build --release` / `./gradlew assembleDebug` /
  ecc. QUI creerebbe un secondo posto che pretende di sapere come
  compilare ogni progetto, garantito a divergere dal `build.sh`/`.bat`
  reale (e già corretto) di quel progetto. `install.py` invece cerca un
  nome di script di build conosciuto (`build.sh`, `build_firmware.sh`,
  `build_exe.sh`, `build-android.sh`, e i loro equivalenti `.bat` - i
  nomi reali usati nei 44 progetti) ed esegue quello che esiste.
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
│   ├── registry.py        # I 44 progetti: repo, stack, file di versione, pattern, obiettivo di distribuzione
│   ├── version_parse.py   # UN'implementazione di estrazione regex, locale+GitHub
│   ├── detect.py          # Scansiona una radice di workspace per ciò che è installato
│   ├── github_client.py   # Recupero concorrente del contenuto raw + ritentativo/backoff reale per errori di rete transitori
│   ├── install.py         # git clone/pull + delega allo script di build proprio
│   ├── qt_gui.py           # Bridge Qt Quick verso i servizi reali di scoperta/aggiornamento
│   ├── qml/Main.qml        # Shell desktop a tema con checkpoint e About
│   ├── gui.py              # Fallback Tkinter se PySide6 non e disponibile
│   └── main.py             # Dispatch: GUI predefinita, --cli per status/install/update
├── build.sh / build.bat    # venv + installazione editabile + compile-check
├── run.sh / run.bat        # GUI predefinita / ingresso CLI
├── run-gui.vbs             # Launcher grafico Windows senza console
└── bump_version.py         # Incremento "contachilometri" dell'ecosistema (pyproject.toml + __init__.py)
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
`build.bat`/`build.sh` lo installano gia). `--cli` non ha dipendenze GUI ed e
l'ingresso corretto per una CM5 headless. Senza Qt, la vecchia finestra
Tkinter resta solo un fallback di compatibilita.

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

## 🚀 ROADMAP

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

## 🔗 PROGETTI CORRELATI

Lo scopo intero di questo strumento è gestire ciascuno degli altri
progetti dell'ecosistema - invece di elencare tutti e 44 qui (vedi
`registry.py` per la lista esatta e autorevole), i due più vicini per
ruolo:

- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - il
  controller di cella multi-robot di punta che questo strumento è
  pensato per mantenere installato e aggiornato sul vero hardware CM5.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** -
  un altro strumento Python autonomo pensato per girare accanto al
  controller di cella, il fratello più vicino per ruolo (un'utilità
  mirata lato CM5, non parte del percorso di controllo dei robot stesso).

**Resto dell'ecosistema** (ogni progetto che questo strumento può
rilevare/installare/aggiornare): i 12 progetti originali (firmware,
server, app mobile/desktop), i nodi IA Vision/Cognitivi, i servizi di
orchestrazione/simulazione in Rust, gli strumenti di
infrastruttura/CLI in Go, i gateway industriali in Node, e il
firmware/strumenti PC della testa utensile URTC - vedi il proprio
raggruppamento di `registry.py` (che corrisponde ai commenti di
struttura delle directory di questo stesso README) per la lista
completa e attuale.

## 👤 AUTORE

**JuanenRac (Electro Hobby 3D)**
Email: electrohobby3d@gmail.com
YouTube: [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENZA

GPL-3.0 (software) / CC BY-SA 4.0 (documentazione) - vedi [LICENSE.md](LICENSE.md).
