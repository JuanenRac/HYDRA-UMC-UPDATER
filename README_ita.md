<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | 🇮🇹 <b>Italiano</b> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📦 Rileva, installa e aggiorna manualmente l'intero ecosistema HYDRA-UMC

<p align="center">
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

**Verifica di onestà - cosa funziona davvero oggi:** la logica di discovery/versione a livello di ecosistema (`registry.py`, `project_manifest.py`, `ecosystem_catalog.py`, `version_parse.py`, `detect.py`), il vero client GitHub raw-content con retry/backoff (`github_client.py`) e la logica clona-prepara-verifica-promuovi della pipeline di installazione/aggiornamento (`install.py`) sono reali e testati - 140 test superati (`pytest tests/`), incluso un server HTTP fittizio che dimostra l'isolamento tra un catalogo malformato e un singolo progetto malformato, più veri round-trip di clone/build git in directory temporanee. `--cli status`/`install`/`update` eseguono lo stesso nucleo testato end-to-end contro il vero host GitHub raw-content live (non un mock) ogni volta che li esegui davvero. La GUI desktop Qt Quick (`qt_gui.py`, `qml/Main.qml`) e il fallback Tkinter legacy (`gui.py`) collegano quello stesso nucleo testato a una finestra reale e sono stati eseguiti su veri checkout dell'ecosistema, ma nessuna delle due ha un test automatico proprio - non esiste `test_gui.py`/`test_qt_gui.py`, poiché qui non si tenta di guidare un vero event loop Qt/Tk. La copertura a 8 lingue di `i18n.py` è verificata da test (`test_i18n.py`), ma solo per la parità delle chiavi tra lingue, non per la qualità della traduzione. Vedi `CHANGELOG.md` per sapere esattamente cosa è stato consegnato finora.

---

> **Stato di sicurezza (safety e security):** questo ecosistema non è un sistema di sicurezza certificato. Non esiste ancora un percorso E-STOP hardware, né limiti o interblocchi imposti dal firmware, né un comando di movimento verificato; le immagini firmware sono controllate con CRC32 e un HMAC-SHA256 a chiave condivisa, non con una firma asimmetrica; TLS e TLS reciproco sono opzionali e disattivati per impostazione predefinita; nessuna scheda propria è stata ancora assemblata o provata. Leggi la [base di sicurezza](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e il [modello delle minacce](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) prima di fidarti di qualsiasi affermazione qui per la sicurezza di una persona.

## 📋 In breve

| | |
|---|---|
| Versione | `0.4.8` |
| Maturità | Consolidato |
| Test | 140 (`pytest tests/`) |
| Tecnologia | Python 3.10+ / PySide6 / Qt Quick (QML) / Tkinter (legacy fallback) / Git / GitHub raw content |
| Destinazione | Il PC di chi lo usa |
| Su hardware reale | Non applicabile: nulla qui gira su hardware |

## 1. 🛠️ PANORAMICA TECNICA

HYDRA-UMC-UPDATER è un piccolo strumento - GUI con finestra per
impostazione predefinita, CLI completa con `--cli` - pensato per girare
sia sul vero CM5 sia sulla macchina Windows/Linux/macOS personale di uno
sviluppatore (qualsiasi workspace con lo stesso tipo di checkout) che
risponde a tre domande per ogni altro progetto reale che scopre tramite
il proprio manifesto `hydra-umc.project.json` di ciascun checkout
vicino - il numero stesso non è mai codificato in modo fisso qui, perché
cresce insieme all'ecosistema:

1. **Cosa c'è realmente installato qui, e in quale versione?**
2. **Qual è l'ultima versione pubblicata su GitHub?**
3. **Se GitHub ha una versione più recente, fammi scegliere un progetto o un lotto sequenziale confermato.**

Quest'ultimo punto è deliberato e non negoziabile: questo strumento non
modifica mai un progetto di propria iniziativa. Un'azione sul progetto
selezionato richiede sempre una conferma esplicita. La GUI può anche offrire
**Installa tutti i mancanti** o **Aggiorna tutti gli obsoleti**: sono lotti
sequenziali confermati separatamente e soggetti agli stessi controlli di
manifest, versione e sicurezza. Non esiste alcun aggiornamento automatico
notturno senza approvazione umana. La conferma mostra i progetti esatti del lotto, nell'ordine in cui verranno eseguiti.

Nemmeno tutti i progetti scoperti appartengono alla CM5 stessa - alcuni sono strumenti che uno sviluppatore esegue dal proprio PC (il firmware viene compilato e flashato DA una postazione di lavoro, non compilato SULLA cella) oppure app installate su un telefono/orologio. Il manifest di ogni progetto indica quale sia il caso (vedi sezione 3) e la tabella dei progetti della GUI può filtrare in base a esso - per impostazione predefinita sono mostrati tutti i progetti, così né l'updater stesso né l'SDK restano nascosti.

Esempio illustrativo (il numero esatto di progetti e ogni numero di
versione qui sotto sono inventati per la forma dell'output, non
un'esecuzione realmente catturata - il numero reale è sempre quello che
`registry.py` scopre oggi, mai una cifra fissa in questo documento):

```
$ hydra-umc-updater --cli status
Workspace root: /home/pi/HYDRA-UMC
PROJECT           MATURITY     ROLE      STACK       LOCAL     GITHUB    STATE
-----------------------------------------------------------------------------
HYDRA-UMC         functional   firmware  firmware-c  0.0.7     0.0.7     up to date
HYDRA-UMC-SERVER  functional   service   node        0.0.5     0.0.9     OUTDATED
HYDRA-UMC-STUDIO  functional   client    node        0.0.8     0.1.3     OUTDATED
...
59/59 installed, 2 outdated
Run `hydra-umc-updater update <project>` to update one by hand - never automatic, see this tool's own README.

$ hydra-umc-updater --cli update HYDRA-UMC-SERVER
Updating HYDRA-UMC-SERVER into /home/pi/HYDRA-UMC ...
OK  Updated /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER to v0.0.9 (commit 1a2b3c4d5e6f) after a verified build; previous installation kept at /home/pi/HYDRA-UMC/HYDRA-UMC-SERVER.backup-9f3c2d1a
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
- **Rilevamento locale**: per ogni progetto scoperto,
  controlla se esiste una directory con quel nome esatto sotto la radice
  del workspace (la disposizione standard dell'ecosistema - ogni
  progetto come directory sorella, esattamente ciò che già presuppongono
  build-frontend.sh e il proprio discovery di HYDRA-UMC-SUITE), e se sì,
  legge la propria copia locale di quello stesso file di versione.
- **Un'unica implementazione di parsing** (`version_parse.py`) è
  condivisa tra la lettura locale e il recupero da GitHub, così un
  checkout locale e un recupero da GitHub non vengono mai interpretati
  da due regex che potrebbero divergere indipendentemente.
- **Installare/aggiornare**: `git clone` (installazione) compila poi
  come passo separato. Aggiornare un checkout GIA' ESISTENTE è invece
  atomico-per-verifica: il candidato viene clonato, unito con
  fast-forward (mai un reset forzato, così vere modifiche locali
  falliscono rumorosamente invece di essere scartate), e compilato/
  verificato PRIMA in un clone di staging completamente indipendente -
  l'installazione reale viene toccata (tramite due rinomine di
  directory consecutive, con l'installazione precedente conservata in
  `<nome>.backup-xxxxxxxx`, mai cancellata) solo se quella build di staging ha
  davvero successo. Un fallimento di build, un checkout divergente/
  sporco, un crash o un disco pieno in qualsiasi momento prima di
  quella promozione finale lasciano l'installazione precedente
  completamente intatta e ancora operativa - vedi il docstring proprio
  di `clone_or_pull` in `install.py`. Il remote git proprio del clone di
  staging viene ripristinato verso il repository GitHub reale subito
  dopo la sua creazione (un semplice clone locale lo lascerebbe invece
  puntare al vecchio percorso di installazione, terminando in silenzio
  tutti i futuri aggiornamenti una volta promosso), e i dati locali
  reali propri del checkout installato (tutto ciò che git considera non
  tracciato o ignorato - `data/settings.json` e simili, esclusi gli
  artefatti di build rigenerabili) vengono trasferiti nel clone di
  staging prima che venga compilato, così lo stato operativo reale di un
  progetto sopravvive a un aggiornamento invece di restare bloccato nel
  checkout `.backup` conservato. In ogni caso questo esegue il
  `build-test.sh`/`build-test.bat` proprio di quel progetto (il
  controllo non-versionante - vedi sezione 3) se ce l'ha. Questo
  strumento non reimplementa mai i passi di build propri di un
  progetto.

- **Barriera di firma opzionale**: lo script `build-test` di un candidato è codice che il candidato porta con sé e che viene eseguito qui prima che qualcosa abbia dimostrato che il commit è del manutentore. Con `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1` l'updater esegue prima `git verify-commit` sul candidato accettato nel clone di staging e, se il commit non ha una firma di cui questa macchina si fida (una chiave gpg nel portachiavi, o un firmatario ssh in `gpg.ssh.allowedSignersFile`), si ferma lì: non viene compilato né eseguito nulla e l'installazione in uso resta intatta. Disattivata per impostazione predefinita, perché richiede sulla macchina un portachiavi che si fidi della chiave del manutentore.

- **Un `.venv` nuovo dopo ogni promozione**: se l'installazione sostituita aveva un `.venv`, il checkout promosso ne riceve uno nuovo (`python -m venv`, poi `pip install -r requirements.txt` se il progetto ha quel file) invece di nessuno; il vecchio resta nel `.backup`. Si disattiva con `HYDRA_UMC_UPDATER_RECREATE_VENV=0` o con l'impostazione salvata `recreate_venv`. Se non si riesce a crearlo, l'aggiornamento è segnalato come fallito e indica il backup che conserva il vecchio.
- **Altre reti di sicurezza**: una sola installazione o aggiornamento alla volta per area di lavoro (file di blocco); un limite di tempo su ogni comando git e su ogni build-test, senza mai chiedere credenziali; un errore imprevisto diventa un risultato fallito nella finestra e nel file di evidenze, mai una finestra bloccata su "in corso"; la barriera di firma copre anche una prima installazione e si può attivare nelle impostazioni salvate (`require_signed_commits`; un file di impostazioni illeggibile vale come attivata), con un avviso rosso nella finestra finché è disattivata; un commit locale che impedisce il fast-forward è nominato nel rifiuto; una nuova installazione la cui build fallisce viene rimossa di nuovo; le cartelle di staging obsolete vengono ripulite all'inizio di un'esecuzione, e `--cli prune-backups [--keep N] [--dry-run]` rimuove le vecchie cartelle `<nome>.backup-xxxxxxxx` solo su richiesta.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Checkpoint reali durante installazione o aggiornamento di HYDRA-UMC-UPDATER" width="100%">
</p>

## 3. 🧱 ARCHITETTURA E DECISIONI DI DESIGN

- **GUI Qt Quick predefinita, `--cli` per headless.** `main.py` controlla
  `--cli` prima di importare il runtime PySide6 opzionale. La CLI funziona su
  una CM5 senza schermo né dipendenze desktop; senza argomenti avvia QML quando
  disponibile e Tkinter resta solo un fallback temporaneo.
- **La GUI con finestra è reale, multilingue in 8 lingue (`i18n.py`) - `--cli` deliberatamente non lo è.** Ogni widget reale si ri-etichetta dal vivo da una `Combobox` di lingua (en/es/fr/it/de/zh/ja/pt, le stesse 8 pubblicate dalla dashboard pubblica e da ogni README), rilevata da una preferenza salvata o dalla locale propria del sistema operativo. I nomi di progetti/famiglie e il testo reale `notes`/`tech` di ciascun progetto restano non tradotti - `registry.py` è la loro unica fonte di verità, e 8 copie parallele di documentazione ingegneristica reale impedirebbero che lo restasse. L'output di `--cli` resta volutamente solo in inglese: è pensato per essere scriptato/reindirizzato, dove un testo stabile e grep-abile conta più della localizzazione.
- **`deploy` è una classificazione, non una restrizione.** Trattare ogni
  progetto scoperto come "una cosa che appartiene al CM5" era sbagliato - i
  repository di firmware vengono compilati e flashati DA un PC (il CM5
  ha bisogno solo del binario risultante via CAN-OTA, mai del codice
  sorgente di questo repository), e diversi strumenti (URTC-FLASHER,
  HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...) sono pensati per girare sul
  proprio posto di lavoro di un operatore, non dentro la cella stessa.
  Il campo `deploy` di `registry.py` ("cm5" / "user-pc" / "mobile" /
  "wearable" / "dev-server") registra questo, e il filtro della GUI lo usa come punto di
  partenza ragionevole - mai come restrizione rigida, dato che questo
  stesso strumento è anche pensato per girare sul PC personale di uno
  sviluppatore, dove ogni progetto scoperto è ugualmente valido da ispezionare.
- **Nessuna logica di build per stack in questo strumento.** L'ecosistema abbraccia 7 toolchain (Python, Rust, Go, Node/TS, Android/Kotlin, Flutter, firmware ARM). Reimplementare `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` / ecc. QUI creerebbe un secondo posto che pretende di sapere come compilare ogni progetto, destinato a divergere dai controlli reali (e già corretti) del progetto stesso. `install.py` esegue invece solo il `build-test.sh` non versionante del progetto (`build-test.bat` su Windows), che verifica senza incrementare alcuna versione; un progetto che non ne ha uno viene rifiutato con "No non-versioning build-test.sh/.bat found".
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
- **La CLI resta esplicita; i lotti GUI restano confermati.** I comandi CLI
  `install`/`update` richiedono un nome di progetto. La GUI può eseguire
  **Installa tutti i mancanti** o **Aggiorna tutti gli obsoleti**, ma solo dopo
  una conferma separata e in sequenza attraverso gli stessi controlli di
  sicurezza. Non esiste aggiornamento automatico non supervisionato.
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
│   ├── i18n.py             # Traduzioni reali e complete della GUI (8 lingue)
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
./run.sh --cli prune-backups --keep 2  # rimuove le vecchie cartelle <nome>.backup-xxxxxxxx (mantiene le 2 più recenti di ciascuna)
```

Su Windows: `build.bat`, poi `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli install <nome>` / `run.bat --cli update <nome>`.

La GUI preferita richiede il runtime Qt opzionale (`pip install -e ".[gui]"`;
`build.bat`/`build.sh` lo installano già). `--cli` non ha dipendenze GUI ed è
l'ingresso corretto per una CM5 headless. Senza Qt, la vecchia finestra
Tkinter resta solo un fallback di compatibilità.

**Risoluzione dei problemi**

- `status` mostra `?` per la versione locale o GitHub di un progetto: il suo file di versione esiste, ma la voce `native_version` del `hydra-umc.project.json` di quel progetto non corrisponde più a dove si trova davvero la sua versione - correggi il manifest di quel progetto.
- `status` mostra `-` per GitHub senza alcun errore mostrato: esegui
  `status` (senza `--offline`) - `-` appare solo quando il controllo
  GitHub è stato saltato del tutto.
- `install`/`update` fallisce con "No non-versioning build-test.sh/.bat found": quel progetto non ha ancora un `build-test.sh`/`build-test.bat` - aggiungigli quello standard dell'ecosistema (deve verificare senza incrementare alcuna versione).
- `git merge --ff-only failed`: il checkout locale ha una cronologia divergente o commit locali (il messaggio li nomina) - spostali o scartali (`git status`/`git log` nella directory di quel progetto) prima di riprovare `update`. Le modifiche non committate ai file tracciati vengono rifiutate subito. Questo strumento non forza mai il reset di un checkout.

## 🚀 TABELLA DI MARCIA

- Un eseguibile GUI autonomo pacchettizzato (PyInstaller, seguendo la
  propria convenzione `build_exe.bat`/`.sh` di HYDRA-UMC-SUITE) per
  un'installazione con doppio clic senza alcun passaggio `pip`/venv -
  oggi la GUI richiede ancora `./build.sh` prima, come la CLI.
- Controllo preliminare opzionale delle dipendenze per progetto
  (segnalare toolchain mancanti - nessun Rust/Go/SDK Android/Flutter
  installato - prima che un `install` fallisca a metà strada).
- Tracciamento per componente per il firmware multi-binario proprio di
  HYDRA-UMC/URTC (vedi la "semplificazione nota" nella sezione 3), non
  appena ci sarà una reale necessità oltre l'unico componente
  rappresentativo tracciato oggi.

## 🔗 Progetti Correlati

Questo progetto fa parte dell'ecosistema robotico HYDRA-UMC dello stesso autore (JuanenRac / Electro Hobby 3D). Vale la pena conoscerlo, poiché una richiesta potrebbe in realtà riguardare uno di questi invece di questo repository.

**Direttamente Correlati**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — il progetto della scheda madre del braccio robotico: host CM5 + coprocessore STM32H745 dual-core, pensato per coordinare fino a 8 bracci utensile via CAN-OTA/SPI-OTA (firmware in fase iniziale; nessuna scheda assemblata per ora).
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro di comando sciame desktop (PySide6) per più server contemporaneamente, pacchettizzato come eseguibile standalone — un altro strumento Python standalone pensato per essere eseguito accanto al controller di cella, il fratello più vicino per ruolo (un'utilità focalizzata lato CM5, non parte del percorso di controllo del robot stesso).
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — dipende da questo progetto come vera libreria per la propria scoperta dell'ecosistema su GitHub durante la costruzione di una nuova immagine della CM5, invece di una seconda implementazione che potrebbe divergere in modo indipendente.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinatore di incidenti di manutenzione: un ruolo edge a basso privilegio raccoglie uno snapshot di inventario/salute sanificato, un ruolo control-plane lo rende in sola lettura e chiede a un provider di IA di suggerire una diagnosi - non applica mai una patch né distribuisce nulla.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host di sviluppo riproducibile (Raspberry Pi 5 / CM5) che conserva il codice sorgente dell'ecosistema ed esegue attività delimitate di build/test tramite una coda durevole; un ruolo di sviluppo dedicato, esplicitamente distinto da un CM5 operativo.

**Fa Anche Parte dell'Ecosistema**

*Hardware e Piattaforma di Base*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — livello prodotto riproducibile su Raspberry Pi OS per il CM5: agente in sola lettura, config/profili validati, provisioning WiFi al primo contatto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — il contratto JSON-Schema condiviso e la barriera software di controllo dei job contro cui ogni bridge valida i propri comandi (non è una funzione di sicurezza certificata).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro dichiarativo e validatore di manifesti adattatore per connettori di macchine esterne; estende la propria idea di contratto dell'SDK alle macchine esterne senza sostituire i progetti di gateway industriale.

*Backend Centrale e Client*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — il vero backend headless (REST/WebSocket) con cui parla davvero ogni client di controllo.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — dashboard di controllo web con visualizzazione 3D multi-robot in tempo reale.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app di controllo nativa per Android con login biometrico e un companion Wear OS abbinato.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app di controllo per iOS/iPadOS (Flutter) con sincronizzazione WebSocket in tempo reale.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaccia touch nativa per il touchscreen DSI da 7" a bordo, incorporata direttamente nel CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creatore/editor grafico desktop di URDF che invia i modelli finiti al catalogo di STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor desktop di modelli STL, che trasforma/sostituisce/rimuove/aggiunge veri pezzi nello stesso catalogo di modelli modificato anche da HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barriera di coordinamento per flotte AGV/AMR tramite un publisher MQTT VDA 5050 (testato solo contro una flotta emulata).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinatore ad alto livello per celle CNC con accesso a stato/byte di controllo GRBL (testato solo contro un emulatore).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barriera di coordinamento per droidi con zampe/umanoidi, con un mittente di comandi per Boston Dynamics Spot (testato solo contro un emulatore).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinatore per celle laser che legge 3 segnali GPIO di chiave/involucro/interblocco (testato solo contro un chip simulato; non può armare né far partire un laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinatore ad alto livello sicuro per il flusso schede del pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barriera di coordinamento sicura per stampanti 3D Moonraker/Klipper, con comandi di lavoro reali e controllati.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinatore con un trasporto ROS 2 rclpy importato in modo lazy (non ancora eseguito contro un'installazione ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barriera di coordinamento per UAV dotati di fotocamera, con un mittente di comandi MAVLink (testato solo contro un emulatore).


*Nodo IA Visione (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub di integrazione per la pipeline di visione Hailo-8, con un vero controllo di prontezza hardware per fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro reale di modelli compilati con verifica di caricamento sicuro per architettura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generatore reale di pipeline GStreamer + config MediaMTX, con una vera barriera di integrazione HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — legge di correzione Position-Based Visual Servoing con autorizzazione condizionata allo stato di zona; ancora nessuna stima di posa da telecamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — logica v0 di violazione zona, freschezza di calibrazione e richiesta E-STOP che legge le posizioni degli oggetti da un file; nessun rilevatore la alimenta e nessun E-STOP fisico è ancora collegato.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub di integrazione per la pipeline cognitiva Hailo-10 (orchestrazione LLM/VLA/voce).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vera codifica/decodifica di token d'azione e generazione di traiettoria per un modello Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vero front-end vocale (VAD + parser di intenti) con un relay verso Watch limitato e soggetto a conferma.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vera scomposizione dei task basata su regole e recupero semantico degli errori sui codici errore MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vera ricerca documentale TF-IDF (solo libreria standard) sui documenti Markdown di questo ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — tecnico di manutenzione IA locale e con cancelli di policy per l'ecosistema stesso - osserva, diagnostica e propone correzioni; i due livelli di rischio più alti non sono deliberatamente ancora implementati.

*Orchestrazione e Sciame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub di integrazione con un vero contratto di health-report gRPC/Protobuf e una macchina a stati di missione.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vera coda di lavori basata su priorità con deduplicazione, su una vera API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vero watchdog di salute della flotta basato su gRPC, con retry/backoff e rilevamento di discrepanza d'identità.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vero pianificatore di percorsi 3D basato su RRT, con vera validazione delle collisioni ostacolo/spazio di lavoro.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vera sincronizzazione di stato CRDT LWW-Element-Map, con property test per la convergenza multi-cella.

*Gemello Digitale e Simulazione*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub di integrazione per il motore di gemello digitale, con un vero contratto di sincronizzazione per compatibilità di versione.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — router hardware-in-the-loop con un interblocco software di collisione tra simulazione e hardware reale (testato senza hardware reale).
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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app companion WearOS con schemi di avviso aptico e un relay vocale verso il telefono abbinato (non ancora eseguita su un orologio fisico).

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
