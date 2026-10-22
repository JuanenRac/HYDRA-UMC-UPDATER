<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 📦 Detecta, instala y actualiza a mano todo el ecosistema HYDRA-UMC

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Core-stdlib%20only-brightgreen.svg" alt="stdlib-only CLI core">
  <img src="https://img.shields.io/badge/Desktop-PySide6%20%7C%20Qt%20Quick-367BF5.svg" alt="PySide6 Qt Quick desktop GUI">
</p>

> **Modo visual de escritorio:** la interfaz de escritorio por defecto usa
> **Qt Quick / QML** mediante el runtime GUI opcional `PySide6`. El núcleo del
> actualizador y el modo `--cli` siguen siendo solo libreria estandar para una CM5 sin pantalla.
>
> **Inicio Windows y evidencia de actualizacion:** abre `run-gui.vbs` (o usa
> `run.bat` sin argumentos) para el cliente grafico sin consola. El panel de
> actualizacion muestra checkpoints reales de precomprobacion, origen,
> manifiesto, build-test y finalizacion con evidencia capturada; `run.bat --cli ...`
> conserva la terminal para diagnosticos.
> Instalar solo se activa si falta el checkout y Actualizar solo si GitHub es
> superior. Durante una accion aprobada, los checkpoints sustituyen los
> controles del proyecto seleccionado; otra seleccion los restaura.
> **Instalar todos los faltantes** y **Actualizar todos los desfasados** son
> acciones de lote secuenciales, confirmadas por separado y basadas en el mismo
> estado real y flujo de seguridad.

**Comprobación de honestidad - lo que realmente funciona hoy:** la lógica de descubrimiento/versión de todo el ecosistema (`registry.py`, `project_manifest.py`, `ecosystem_catalog.py`, `version_parse.py`, `detect.py`), el cliente real de GitHub raw-content con reintento/backoff (`github_client.py`) y la lógica del pipeline de instalación/actualización de clonar-preparar-verificar-promover (`install.py`) son reales y están probados - 140 tests que pasan (`pytest tests/`), incluido un servidor HTTP de fixture que demuestra el aislamiento entre un catálogo malformado y un solo proyecto malformado, además de round-trips reales de clonado/build de git en directorios temporales. `--cli status`/`install`/`update` ejercitan ese mismo núcleo probado de extremo a extremo contra el host real y en vivo de GitHub raw-content (no un mock) cada vez que realmente los ejecutas. La GUI de escritorio Qt Quick (`qt_gui.py`, `qml/Main.qml`) y el respaldo heredado en Tkinter (`gui.py`) conectan ese mismo núcleo probado a una ventana real y se han ejecutado en checkouts reales del ecosistema, pero ninguna de las dos tiene un test automatizado propio - no existe `test_gui.py`/`test_qt_gui.py`, ya que aquí no se intenta manejar un bucle de eventos real de Qt/Tk. La cobertura de 8 idiomas de `i18n.py` está reforzada por test (`test_i18n.py`), pero solo para la paridad de claves entre idiomas, no para la calidad de la traducción. Consulta `CHANGELOG.md` para ver exactamente qué se ha entregado hasta ahora.

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado. Todavía no existe una ruta de E-STOP por hardware, ni límites ni enclavamientos aplicados por el firmware, ni un comando de movimiento verificado; las imágenes de firmware se comprueban con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica; TLS y TLS mutuo son opcionales y están desactivados por defecto; aún no se ha poblado ni probado ninguna placa propia. Lee la [línea base de seguridad](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.4.8` |
| Madurez | Establecido |
| Tests | 140 (`pytest tests/`) |
| Tecnología | Python 3.10+ / PySide6 / Qt Quick (QML) / Tkinter (legacy fallback) / Git / GitHub raw content |
| Destino | El PC de quien lo usa |
| En hardware real | No aplica: nada de esto se ejecuta en hardware |

## 1. 🛠️ VISIÓN TÉCNICA

HYDRA-UMC-UPDATER es una pequeña herramienta - GUI con ventana por
defecto, CLI completa con `--cli` - pensada para ejecutarse tanto en la
CM5 real como en la propia máquina Windows/Linux/macOS de un
desarrollador (cualquier workspace con el mismo tipo de checkout) que
responde a tres preguntas sobre cada otro proyecto real que descubre a
través del propio manifiesto `hydra-umc.project.json` de cada checkout
vecino - el número en sí nunca está fijado aquí, ya que crece con el
propio ecosistema:

1. **¿Qué hay instalado aquí de verdad, y en qué versión?**
2. **¿Cuál es la última versión publicada en GitHub?**
3. **Si GitHub tiene una versión más nueva, déjame elegir un proyecto o un lote secuencial confirmado.**

Ese último punto es deliberado y no negociable: esta herramienta nunca cambia
un proyecto por iniciativa propia. Una acción sobre un proyecto seleccionado
siempre exige confirmación explícita. La GUI también puede ofrecer **Instalar
todos los faltantes** o **Actualizar todos los desfasados**; ambos son lotes
secuenciales confirmados por separado y sujetos a las mismas puertas de
manifiesto, versión y seguridad. Nunca existe actualización automática nocturna
sin una persona aprobando la acción exacta. La confirmación muestra los proyectos exactos del lote, en el orden en que se ejecutarán.

Tampoco todo proyecto descubierto pertenece a la CM5 en sí - algunos son herramientas que un desarrollador ejecuta desde su propio PC (el firmware se compila y se flashea DESDE un puesto de trabajo, no se compila EN la célula), o apps que se instalan en un móvil/reloj. El manifiesto de cada proyecto registra cuál es cuál (ver sección 3), y la tabla de proyectos de la GUI puede filtrar por él - por defecto se muestran todos los proyectos, así que ni el propio actualizador ni el SDK quedan ocultos.

Ejemplo ilustrativo (el número exacto de proyectos y cada número de
versión de abajo están inventados para mostrar la forma de la salida,
no son una ejecución realmente capturada - el número real es siempre
el que `registry.py` descubre hoy, nunca una cifra fija en este
documento):

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

Ejecutar `hydra-umc-updater` sin argumentos (o hacer doble clic) abre la
misma información en una ventana - una tabla de proyectos, un filtro por
destino de despliegue, y botones de Instalar/Actualizar para la fila
seleccionada.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_1.png" alt="Vista general real del escritorio de HYDRA-UMC-UPDATER" width="100%">
</p>

## 2. 🔄 CÓMO FUNCIONA REALMENTE UNA COMPROBACIÓN/ACTUALIZACIÓN

- **Origen de la versión**: la convención "cuentakilómetros" de
  auto-incremento de este ecosistema (cada build real incrementa un
  número de versión que vive DENTRO de un archivo fuente -
  `pyproject.toml`, `Cargo.toml`, `version.go`, `package.json`,
  `version.properties`, `pubspec.yaml`, o un `#define` de firmware, según
  el stack del proyecto) nunca ha creado un tag de git ni un GitHub
  Release para ese incremento. Por eso esta herramienta lee el MISMO
  archivo que el propio `bump_version.py`/script de build de cada
  proyecto ya escribe, directamente desde la rama por defecto del repo
  vía el servidor de contenido raw de GitHub - no la API de Releases, que
  reportaría que todos los proyectos no tienen ningún release.
- **Detección local**: para cada proyecto descubierto,
  comprueba si existe un directorio con ese nombre exacto bajo la raíz
  del workspace (la disposición estándar del ecosistema - cada proyecto
  como directorio hermano, lo mismo que ya asumen build-frontend.sh y el
  propio descubrimiento de HYDRA-UMC-SUITE), y si existe, lee su propia
  copia local de ese mismo archivo de versión.
- **Una sola implementación de parseo** (`version_parse.py`) se comparte
  entre la lectura local y la descarga de GitHub, así que un checkout
  local y una descarga de GitHub nunca se interpretan con dos regex que
  puedan desincronizarse de forma independiente.
- **Instalar/actualizar**: `git clone` (instalar) compila después como
  un paso aparte. Actualizar un checkout YA EXISTENTE es atómico por
  verificación en su lugar: el candidato se clona, se fusiona con
  fast-forward (nunca un reset forzado, así que los cambios locales
  reales fallan de forma visible en vez de descartarse), y se compila/
  verifica en un clon de staging completamente independiente PRIMERO -
  la instalación real solo se toca (mediante dos renombrados de
  directorio consecutivos, conservando la instalación anterior en
  `<nombre>.backup-xxxxxxxx`, sin borrarla) si esa compilación de staging
  realmente tiene éxito. Un fallo de compilación, un checkout divergente/
  sucio, un corte de luz o un disco lleno en cualquier momento antes de
  esa promoción final dejan la instalación anterior completamente
  intacta y operativa - ver el propio docstring de `clone_or_pull` en
  `install.py`. El propio remoto git del clon de staging se restaura al
  origen real de GitHub justo después de crearse (un clon local simple
  lo dejaría apuntando a la ruta de instalación antigua, terminando en
  silencio con todas las actualizaciones futuras una vez promovido), y
  los datos locales reales del checkout instalado (todo lo que git
  considera sin seguimiento o ignorado - `data/settings.json` y
  similares, excluyendo artefactos de build regenerables) se trasladan
  al clon de staging antes de compilar, de modo que el estado operativo
  real de un proyecto sobrevive a una actualización en vez de quedar
  varado en el checkout `.backup` conservado. En cualquier caso esto ejecuta el `build-test.sh`/
  `build-test.bat` propio de ese proyecto (la comprobación no-versionada
  - ver sección 3) si lo tiene. Esta herramienta nunca reimplementa los
  pasos de build propios de un proyecto.

- **Puerta opcional de firma**: el script `build-test` de un candidato es código que el propio candidato trae consigo y que se ejecuta aquí antes de que nada haya demostrado que el commit es del mantenedor. Con `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1` el actualizador ejecuta primero `git verify-commit` sobre el candidato aceptado en el clon de staging y, si el commit no tiene una firma en la que esta máquina confíe (una clave gpg en el llavero, o un firmante ssh en `gpg.ssh.allowedSignersFile`), se detiene ahí: no se compila ni se ejecuta nada y la instalación en uso queda intacta. Desactivada por defecto, porque necesita un llavero en la máquina que confíe en la clave del mantenedor.

- **Más redes de seguridad**: una sola instalación o actualización a la vez por espacio de trabajo (fichero de bloqueo); límite de tiempo en cada comando git y en cada build-test, sin pedir credenciales; un error inesperado es un resultado fallido en la ventana y en el fichero de evidencia, nunca una ventana bloqueada en "trabajando"; la puerta de firma cubre también una primera instalación y puede activarse en los ajustes guardados (`require_signed_commits`; un fichero de ajustes ilegible cuenta como activada), con un aviso rojo en la ventana mientras está desactivada; un commit local que impide el avance rápido se nombra en la negativa; una instalación nueva cuya compilación falla se vuelve a eliminar; las carpetas de staging obsoletas se limpian al empezar una ejecución, y `--cli prune-backups [--keep N] [--dry-run]` elimina las carpetas `<nombre>.backup-xxxxxxxx` antiguas solo bajo petición.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Checkpoints reales durante la instalación o actualización de HYDRA-UMC-UPDATER" width="100%">
</p>

## 3. 🧱 ARQUITECTURA Y DECISIONES DE DISEÑO

- **GUI Qt Quick por defecto, `--cli` para headless.** `main.py` comprueba
  `--cli` antes de importar el runtime opcional PySide6. La CLI funciona en
  una CM5 sin pantalla ni dependencia de escritorio; sin argumentos inicia
  QML cuando esta disponible y Tkinter queda solo como fallback temporal.
- **La GUI con ventana es real, multilingüe en 8 idiomas (`i18n.py`) - `--cli` deliberadamente no lo es.** Cada widget real se reetiqueta en vivo desde un `Combobox` de idioma (en/es/fr/it/de/zh/ja/pt, los mismos 8 que publican el dashboard público y todos los README), detectado a partir de una preferencia guardada o del propio locale del sistema operativo. Los nombres de proyectos/familias y el propio texto real de `notes`/`tech` de cada proyecto permanecen sin traducir - `registry.py` es su única fuente de verdad, y 8 copias paralelas de documentación de ingeniería real dejarían de serlo. La salida de `--cli` permanece solo en inglés a propósito: está pensada para ser scripteada/canalizada, donde un texto estable y buscable con grep importa más que la localización.
- **`deploy` es una clasificación, no una restricción.** Tratar todo
  proyecto descubierto como "algo que pertenece a la CM5" era un error - los repos
  de firmware se compilan y se flashean DESDE un PC (la CM5 solo necesita
  el binario resultante vía CAN-OTA, nunca el código fuente de este repo),
  y varias herramientas (URTC-FLASHER, HYDRA-UMC-SUITE,
  HYDRA-UMC-TOOL-CLI, ...) están pensadas para correr en el propio puesto
  de trabajo de un operador, no dentro de la célula misma. El campo
  `deploy` de `registry.py` ("cm5" / "user-pc" / "mobile" / "wearable" / "dev-server")
  registra eso, y el filtro de la GUI lo usa como punto de partida
  razonable - nunca como una restricción dura, ya que esta misma
  herramienta también está pensada para correr en el PC de un
  desarrollador, donde todo proyecto descubierto es igual de válido de inspeccionar.
- **Esta herramienta no contiene lógica de compilación por stack.** El ecosistema abarca 7 toolchains (Python, Rust, Go, Node/TS, Android/Kotlin, Flutter, firmware ARM). Reimplementar `npm install && npm run build` / `cargo build --release` / `./gradlew assembleDebug` / etc. AQUÍ crearía un segundo lugar que dice saber compilar cada proyecto, garantizado a desviarse de las comprobaciones reales (y ya correctas) del propio proyecto. En su lugar, `install.py` ejecuta solo el `build-test.sh` no versionante del propio proyecto (`build-test.bat` en Windows), que verifica sin incrementar ninguna versión; un proyecto que no lo tenga se rechaza con "No non-versioning build-test.sh/.bat found".
- **Contenido raw de GitHub, no la API de Releases.** Ver sección 2 - la
  convención de versionado de este ecosistema nunca crea un tag/release,
  así que la API de Releases sería activamente incorrecta aquí, no solo
  menos conveniente.
- **Un fallo de red transitorio recibe un reintento real; una respuesta
  definitiva nunca.** Cada petición real a GitHub (`_urlopen_with_retries`
  de `github_client.py`) reintenta hasta 3 veces con backoff, pero solo
  cuando la conexión nunca llegó a obtener respuesta alguna (DNS/timeout/
  reset). Un estado HTTP real que GitHub sí devolvió - 404, 403, 500 -
  nunca se reintenta: GitHub ya respondió, y volver a golpearlo solo
  gastaría más límite de peticiones para el mismo resultado.
- **Un catálogo remoto malformado falla de forma ruidosa; un proyecto
  malformado no.** Si el propio listado de repositorios de GitHub es
  inalcanzable o no se puede parsear, `discover_remote_projects()` lanza
  una excepción - tanto `gui.py` como `main.py` ya la capturan y caen de
  vuelta a la lista de proyectos descubierta localmente en vez de mostrar
  un escaneo roto o vacío. El manifiesto malformado de un solo
  repositorio, en cambio, se aísla en la propia lista `errors` de ese
  escaneo y nunca aborta el descubrimiento del resto - una prueba real
  con servidor de fixtures (`tests/test_github_client.py`) demuestra
  ambos caminos.
- **La CLI es explícita; los lotes de la GUI se confirman.** Los comandos
  `install`/`update` de CLI reciben un nombre de proyecto. La GUI puede ejecutar
  **Instalar todos los faltantes** o **Actualizar todos los desfasados**, pero
  solo tras una confirmación independiente y de forma secuencial a través de
  las mismas puertas de seguridad. No existe actualización automática sin
  supervisión.
- **Solo librería estándar.** `urllib` para las descargas de GitHub
  (`github_client.py`), `subprocess` para las llamadas a git/scripts de
  build (`install.py`), nada más - que una herramienta responsable de
  mantener sanas las dependencias de TODOS los demás proyectos se quede
  sin dependencias propias es deliberado.
- **Simplificación conocida**: HYDRA-UMC y URTC son repos de firmware
  multi-componente reales (6 y 4 binarios versionados de forma
  independiente cada uno - ver su propio `VERSION_CHECKLIST.txt`/
  `build_firmware.sh`) sin un único número de versión. `registry.py`
  sigue UN componente representativo por repo - suficiente para
  responder "¿este repo está más o menos al día?", no un sustituto del
  propio `firmware_manifest.json` de `build_firmware.sh` para un flasheo
  real.

## 📂 ESTRUCTURA DE DIRECTORIOS

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py         # ProjectEntry - sin catálogo estático; se construye en tiempo de descubrimiento desde el manifiesto propio de cada repo
│   ├── project_manifest.py # Lee/valida un hydra-umc.project.json propio de cada repositorio
│   ├── ecosystem_catalog.py # Parser del catálogo público de descubrimiento del ecosistema de JuanenRac
│   ├── version_parse.py   # UNA implementación de extracción por regex, local+GitHub
│   ├── detect.py          # Escanea una raíz de workspace para ver qué está instalado
│   ├── github_client.py   # Descarga concurrente del contenido raw + reintento/backoff real ante errores de red transitorios
│   ├── install.py         # git clone/pull + delega en el script de build propio
│   ├── i18n.py             # Traducciones reales y completas de la GUI (8 idiomas)
│   ├── qt_gui.py           # Puente Qt Quick hacia los servicios reales de descubrimiento/actualizacion
│   ├── qml/Main.qml        # Shell de escritorio con tema, checkpoints y About
│   ├── gui.py              # Fallback Tkinter si PySide6 no esta disponible
│   └── main.py             # Despacho: GUI por defecto, --cli para status/install/update
├── tests/                  # Tests reales: github_client, i18n, install, project_manifest, registry
├── docs/
│   ├── CLI_REFERENCE.md     # Referencia de comandos
│   └── QML_DESKTOP_GUI.md   # Arquitectura de la GUI Qt Quick
├── images/                 # Medios, iconos de app y capturas de la interfaz
├── tools/
│   ├── build_test.py        # Comprobación de compilación sin versionado
│   ├── ci_validate.py       # Validación de manifiesto/CHANGELOG/docs usada por CI
│   ├── generate_app_icon.py # Renderiza el SVG público de HYDRA-UMC al icono que consume Windows
│   ├── migrate_project_manifests.py  # Audita un workspace tras la migración de manifiestos de un solo uso
│   └── validate_project_manifests.py # Valida manifiestos propios de cada repo + versiones nativas de build
├── .env.example            # Plantilla de variables de entorno
├── build.sh / build.bat    # venv + instalación editable + compile-check
├── run.sh / run.bat        # GUI por defecto / entrada CLI
├── run-gui.vbs             # Lanzador grafico Windows sin ventana de consola
├── bump_version.py         # Incremento "cuentakilómetros" del ecosistema (pyproject.toml + __init__.py)
└── bump_manifest_version.py # Sincroniza la versión de hydra-umc.project.json con la nativa (--sync)
```

## ⚙️ COMPILACIÓN Y EJECUCIÓN

```bash
chmod +x build.sh   # una sola vez
./build.sh          # crea .venv, pip install -e ., compile-check de todo
./run.sh                                # GUI con ventana (por defecto)
./run.sh --cli status                   # qué está instalado, versión local vs. GitHub
./run.sh --cli status --offline         # lo mismo, sin comprobar GitHub
./run.sh --cli install <NOMBRE-PROYECTO> # clona + compila un proyecto aún no instalado
./run.sh --cli update  <NOMBRE-PROYECTO> # actualiza + recompila un proyecto ya instalado
./run.sh --cli prune-backups --keep 2  # elimina las carpetas <nombre>.backup-xxxxxxxx antiguas (conserva las 2 más recientes de cada una)
```

En Windows: `build.bat`, y luego `run.bat` (GUI) / `run.bat --cli status`
/ `run.bat --cli install <nombre>` / `run.bat --cli update <nombre>`.

La GUI preferida necesita el runtime Qt opcional (`pip install -e ".[gui]"`;
`build.bat`/`build.sh` ya lo instalan). `--cli` no tiene dependencia grafica y
es la entrada correcta para una CM5 headless. Si Qt no esta disponible, la
antigua ventana Tkinter es solo un fallback de compatibilidad.

**Solución de problemas**

- `status` muestra `?` en la versión local o de GitHub de un proyecto: su fichero de versión existe, pero la entrada `native_version` del `hydra-umc.project.json` de ese proyecto ya no coincide con dónde vive realmente su versión - corrige el manifiesto de ese proyecto.
- `status` muestra `-` en GitHub sin ningún error: ejecuta `status` (sin
  `--offline`) - `-` solo aparece cuando la comprobación de GitHub se
  omitió por completo.
- `install`/`update` falla con "No non-versioning build-test.sh/.bat found": ese proyecto aún no tiene `build-test.sh`/`build-test.bat` - añádele el estándar del ecosistema (debe verificar sin subir ninguna versión).
- `git merge --ff-only failed`: el checkout local tiene un historial divergente o commits locales (el mensaje los nombra) - muévelos o descártalos (`git status`/`git log` en el directorio de ese proyecto) antes de reintentar `update`. Las ediciones sin confirmar de ficheros versionados se rechazan de entrada. Esta herramienta nunca fuerza el reseteo de un checkout.

## 🚀 HOJA DE RUTA

- Un ejecutable de GUI independiente empaquetado (PyInstaller, siguiendo
  la propia convención `build_exe.bat`/`.sh` de HYDRA-UMC-SUITE) para una
  instalación con doble clic sin ningún paso de `pip`/venv - hoy la GUI
  todavía necesita `./build.sh` primero, igual que la CLI.
- Comprobación previa opcional de dependencias por proyecto (avisar de
  toolchains faltantes - sin Rust/Go/SDK de Android/Flutter instalado -
  antes de que un `install` falle a mitad de camino).
- Seguimiento por componente para el firmware multi-binario propio de
  HYDRA-UMC/URTC (ver la "simplificación conocida" de la sección 3), en
  cuanto haya una necesidad real más allá del único componente
  representativo que se sigue hoy.

## 🔗 Proyectos Relacionados

Este proyecto es parte del ecosistema de robótica HYDRA-UMC del mismo autor (JuanenRac / Electro Hobby 3D). Vale la pena conocerlo, ya que una petición podría en realidad ser sobre alguno de estos en vez de sobre este repositorio.

**Directamente Relacionados**
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — el diseño de la placa madre del brazo robótico: host CM5 + coprocesador STM32H745 de doble núcleo, pensado para coordinar hasta 8 brazos herramienta por CAN-OTA/SPI-OTA (firmware en fase temprana; todavía no hay ninguna placa poblada).
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de mando de enjambre de escritorio (PySide6) para varios servidores a la vez, empaquetado como ejecutable independiente — otra herramienta Python independiente pensada para ejecutarse junto al controlador de celda, el hermano más cercano en cuanto a rol (una utilidad enfocada del lado del CM5, no parte del propio camino de control del robot).
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — depende de este proyecto como una librería real para su propio descubrimiento del ecosistema en GitHub al construir una imagen nueva de la CM5, en vez de una segunda implementación que pueda divergir de forma independiente.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinador de incidencias de mantenimiento: un rol edge de bajo privilegio recopila un snapshot de inventario/salud saneado, un rol control-plane lo renderiza de solo lectura y pide a un proveedor de IA que sugiera un diagnóstico - nunca aplica un parche ni despliega nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — host de desarrollo reproducible (Raspberry Pi 5 / CM5) que almacena el código del ecosistema y ejecuta tareas acotadas de compilación/pruebas bajo una cola duradera; un rol de desarrollo dedicado, explícitamente distinto de un CM5 operativo.

**También Forma Parte del Ecosistema**

*Hardware y Plataforma Base*
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — capa de producto reproducible sobre Raspberry Pi OS para el CM5: agente de solo lectura, config/perfiles validados, aprovisionamiento WiFi de primer contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — el contrato JSON-Schema compartido y la barrera de software de puerta de trabajos contra la que cada bridge valida sus comandos (no es una función de seguridad certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registro declarativo y validador de manifiestos de adaptador para conectores de máquinas externas; extiende la propia idea de contrato del SDK a máquinas externas sin sustituir a los proyectos de pasarela industrial.

*Backend Central y Clientes*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — el backend headless real (REST/WebSocket) con el que habla de verdad cada cliente de control.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — panel de control web con visualización 3D multi-robot en tiempo real.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — app nativa de control para Android con inicio de sesión biométrico y un compañero Wear OS emparejado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — app de control para iOS/iPadOS (Flutter) con sincronización en tiempo real por WebSocket.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interfaz táctil nativa para la pantalla táctil DSI de 7" a bordo, embebida en el propio CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — creador/editor gráfico de URDF de escritorio que envía los modelos terminados al propio catálogo de STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de escritorio de modelos STL, que transforma/reemplaza/quita/añade piezas reales en el mismo catálogo de modelos que también edita HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — barrera de coordinación para flotas AGV/AMR mediante un publicador MQTT VDA 5050 (probado solo contra una flota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinador de alto nivel para celdas CNC con acceso a estado/bytes de control GRBL (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — barrera de coordinación para droides con patas/humanoides, con un emisor de comandos para Boston Dynamics Spot (probado solo contra un emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinador de celdas láser que lee 3 señales GPIO de llave/carcasa/enclavamiento (probado solo contra un chip simulado; no puede armar ni disparar un láser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinador de alto nivel seguro para el flujo de placas de pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — barrera de coordinación segura para impresoras 3D Moonraker/Klipper, con comandos de trabajo reales y controlados.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinador con un transporte ROS 2 rclpy importado de forma perezosa (todavía no ejecutado contra una instalación de ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — barrera de coordinación para UAV equipados con cámara, con un emisor de comandos MAVLink (probado solo contra un emulador).


*Nodo IA de Visión (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — nodo de integración para el pipeline de visión Hailo-8, con una comprobación real de disponibilidad de hardware por etapa.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registro real de modelos compilados con verificación de carga segura por arquitectura Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — generador real de pipeline GStreamer + config MediaMTX, con una frontera de integración HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — ley de corrección Position-Based Visual Servoing con autorización condicionada al estado de zona; todavía sin estimación de pose por cámara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de invasión de zona, vigencia de calibración y solicitud de E-STOP que toma las posiciones de los objetos de un fichero; ningún detector la alimenta y todavía no hay un E-STOP físico conectado.

*Nodo IA Cognitivo (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — nodo de integración para el pipeline cognitivo Hailo-10 (orquestación de LLM/VLA/voz).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificación/decodificación real de tokens de acción y generación de trayectoria para un modelo Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — front-end de voz real (VAD + analizador de intención) con un relé a Watch acotado y con confirmación.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — descomposición real de tareas basada en reglas y recuperación semántica de errores sobre códigos de error del MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — búsqueda real de documentos TF-IDF (solo librería estándar) sobre los propios documentos Markdown de este ecosistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de mantenimiento con IA local y con puertas de política para el propio ecosistema - observa, diagnostica y propone arreglos; los dos niveles de riesgo más altos están deliberadamente sin implementar todavía.

*Orquestación y Enjambre*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — nodo de integración con un contrato real de informe de salud gRPC/Protobuf y una máquina de estados de misión.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — cola de trabajos real basada en prioridad con deduplicación, sobre una API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — watchdog de salud de flota real basado en gRPC, con reintento/backoff y detección de discrepancia de identidad.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planificador de rutas 3D real basado en RRT, con validación real de colisión de obstáculos/espacio de trabajo.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronización de estado real mediante CRDT LWW-Element-Map, con pruebas de propiedades para convergencia multi-celda.

*Gemelo Digital y Simulación*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — nodo de integración para el motor de gemelo digital, con un contrato real de sincronización por compatibilidad de versión.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — enrutador hardware-in-the-loop con un enclavamiento de software por colisión entre simulación y hardware real (probado sin hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática directa real y validación de límites articulares sobre un subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generador real de escenas 2D procedurales con exportación de anotaciones YOLO/COCO.

*Datos y Analítica*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — almacén de series temporales real respaldado por sqlite3, con una API HTTP real de ingesta/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detector de anomalías real basado en FFT + línea base estadística, con monitorización de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidad sobre el histórico de DATALAKE, con exportación CSV reproducible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingesta CAN/WebSocket hacia DATALAKE, con deduplicación por secuencia.

*Pasarela Industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — nodo de integración que retransmite a protocolos industriales, con una capa real de lista blanca de comandos/contrapresión.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espacio de direcciones OPC-UA real, verificado con una sesión de cliente real del protocolo binario.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real con autenticación por cliente opcional y ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML reales `/probe` y `/current` de MTConnect, con salida en modo degradado.

*Herramientas Complementarias y Operaciones del Ecosistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — paneles de Resúmenes Inteligentes y Resaltado de Anomalías sobre DATALAKE/ANOMALY-DETECTOR, con un respaldo estadístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flota con un contrato real y estable de códigos de salida, cliente real y en vivo de la propia API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — app compañera de WearOS con patrones de alerta háptica y un relé de voz al teléfono emparejado (todavía no ejecutada en un reloj físico).

---

## 📚 Documentación y Comunidad

- **[docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** — cada subcomando de `--cli`, salida real capturada de una instalación real, y el contrato de códigos de salida.
- **[docs/QML_DESKTOP_GUI.md](docs/QML_DESKTOP_GUI.md)** — cómo está estructurado el cliente de escritorio Qt Quick/QML, y cómo sigue siendo una superficie de control real sobre el mismo backend que usa `--cli`, no una segunda implementación.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológico y pautas de codificación para un pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de enfoque en seguridad de este proyecto.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

GPL-3.0 (software) / CC BY-SA 4.0 (documentación) - ver [LICENSE.md](LICENSE.md).
