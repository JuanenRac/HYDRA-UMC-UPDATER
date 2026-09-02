<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center"><a href="README.md">🇺🇸 English</a> | 🇪🇸 <b>Español</b> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📦 Detecta, instala y actualiza a mano todo el ecosistema HYDRA-UMC/URTC

<p align="left">
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

---

## 1. 🛠️ VISIÓN TÉCNICA

HYDRA-UMC-UPDATER es una pequeña herramienta - GUI con ventana por
defecto, CLI completa con `--cli` - pensada para ejecutarse tanto en la
CM5 real como en la propia máquina Windows/Linux/macOS de un
desarrollador (cualquier workspace con el mismo tipo de checkout) que
responde a tres preguntas sobre cada uno de los otros 44 proyectos del
ecosistema:

1. **¿Qué hay instalado aquí de verdad, y en qué versión?**
2. **¿Cuál es la última versión publicada en GitHub?**
3. **Si GitHub tiene una versión más nueva, déjame actualizar ESE proyecto, a mano.**

Ese último punto es deliberado y no negociable: esta herramienta nunca
actualiza más de un proyecto por comando, y nunca por iniciativa propia.
Una célula de control de robots no es algo que uno quiera que se
actualice solo por la noche - cada actualización real es un comando (o un
clic en un botón, sobre una fila seleccionada en la tabla de la GUI) que
una persona provocó, para un proyecto con nombre, cuyo resultado puede
ver antes de tocar el siguiente.

Tampoco los 44 proyectos pertenecen a la CM5 en sí - la mayoría de los
repos con prefijo URTC y algunos de HYDRA-UMC son herramientas que un
desarrollador ejecuta desde su propio PC (el firmware se compila y se
flashea DESDE un puesto de trabajo, no se compila EN la célula), o apps
que se instalan en un móvil/reloj. El propio campo `deploy` de
`registry.py` registra cuál es cuál (ver sección 3), y la tabla de
proyectos de la GUI filtra por él - por defecto muestra "solo CM5" cuando
detecta que se ejecuta en Linux (el propio SO de la CM5 real), y "mostrar
todo" en Windows/macOS.

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
- **Detección local**: para cada uno de los 44 proyectos conocidos,
  comprueba si existe un directorio con ese nombre exacto bajo la raíz
  del workspace (la disposición estándar del ecosistema - cada proyecto
  como directorio hermano, lo mismo que ya asumen build-frontend.sh y el
  propio descubrimiento de HYDRA-UMC-SUITE), y si existe, lee su propia
  copia local de ese mismo archivo de versión.
- **Una sola implementación de parseo** (`version_parse.py`) se comparte
  entre la lectura local y la descarga de GitHub, así que un checkout
  local y una descarga de GitHub nunca se interpretan con dos regex que
  puedan desincronizarse de forma independiente.
- **Instalar/actualizar**: `git clone` (instalar) o `git pull --ff-only`
  (actualizar - nunca un reset forzado, así que los cambios locales
  reales fallan de forma visible en vez de descartarse), y luego ejecuta
  el `build.sh`/`build.bat` propio de ese proyecto (o un equivalente
  conocido - ver sección 3). Esta herramienta nunca reimplementa los
  pasos de build propios de un proyecto - ver sección 3 para el porqué.

<p align="center">
  <img src="images/HYDRA_UMC_UPDATER_INTERFACE_2.png" alt="Checkpoints reales durante la instalación o actualización de HYDRA-UMC-UPDATER" width="100%">
</p>

## 3. 🧱 ARQUITECTURA Y DECISIONES DE DISEÑO

- **GUI Qt Quick por defecto, `--cli` para headless.** `main.py` comprueba
  `--cli` antes de importar el runtime opcional PySide6. La CLI funciona en
  una CM5 sin pantalla ni dependencia de escritorio; sin argumentos inicia
  QML cuando esta disponible y Tkinter queda solo como fallback temporal.
- **La GUI con ventana es real, multilingüe en 7 idiomas (`i18n.py`) - `--cli` deliberadamente no lo es.** Cada widget real se reetiqueta en vivo desde un `Combobox` de idioma (en/es/fr/it/de/zh/ja, los mismos 7 que publican el dashboard público y todos los README), detectado a partir de una preferencia guardada o del propio locale del sistema operativo. Los nombres de proyectos/familias y el propio texto real de `notes`/`tech` de cada proyecto permanecen sin traducir - `registry.py` es su única fuente de verdad, y 7 copias paralelas de documentación de ingeniería real dejarían de serlo. La salida de `--cli` permanece solo en inglés a propósito: está pensada para ser scripteada/canalizada, donde un texto estable y buscable con grep importa más que la localización.
- **`deploy` es una clasificación, no una restricción.** Tratar los 44
  proyectos como "cosas que pertenecen a la CM5" era un error - los repos
  de firmware se compilan y se flashean DESDE un PC (la CM5 solo necesita
  el binario resultante vía CAN-OTA, nunca el código fuente de este repo),
  y varias herramientas (URTC-FLASHER, HYDRA-UMC-SUITE,
  HYDRA-UMC-TOOL-CLI, ...) están pensadas para correr en el propio puesto
  de trabajo de un operador, no dentro de la célula misma. El campo
  `deploy` de `registry.py` ("cm5" / "user-pc" / "mobile" / "wearable")
  registra eso, y el filtro de la GUI lo usa como punto de partida
  razonable - nunca como una restricción dura, ya que esta misma
  herramienta también está pensada para correr en el PC de un
  desarrollador, donde los 44 son igual de válidos de inspeccionar.
- **Sin lógica de build por stack en esta herramienta.** El ecosistema
  abarca 7 toolchains (Python, Rust, Go, Node/TS, Android/Kotlin,
  Flutter, firmware ARM). Reimplementar `npm install && npm run build` /
  `cargo build --release` / `./gradlew assembleDebug` / etc. AQUÍ
  crearía un segundo sitio que dice saber cómo compilar cada proyecto,
  garantizado a desincronizarse del `build.sh`/`.bat` real (y ya
  correcto) de ese proyecto. `install.py` en cambio busca un nombre de
  script de build conocido (`build.sh`, `build_firmware.sh`,
  `build_exe.sh`, `build-android.sh`, y sus equivalentes `.bat` - los
  nombres reales usados en los 44 proyectos) y ejecuta el que exista.
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
- **`install`/`update` siempre reciben el nombre de un proyecto
  explícito.** No existe un subcomando "actualizar todo", y es una
  decisión de diseño, no una funcionalidad que falte - una flota de
  robots reales no es algo que se deje actualizando solo sin supervisión.
  `status` muestra qué está desactualizado; una persona elige cuál tocar
  de verdad.
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
│   ├── registry.py        # Los 44 proyectos: repo, stack, archivo de versión, patrón, destino de despliegue
│   ├── version_parse.py   # UNA implementación de extracción por regex, local+GitHub
│   ├── detect.py          # Escanea una raíz de workspace para ver qué está instalado
│   ├── github_client.py   # Descarga concurrente del contenido raw + reintento/backoff real ante errores de red transitorios
│   ├── install.py         # git clone/pull + delega en el script de build propio
│   ├── qt_gui.py           # Puente Qt Quick hacia los servicios reales de descubrimiento/actualizacion
│   ├── qml/Main.qml        # Shell de escritorio con tema, checkpoints y About
│   ├── gui.py              # Fallback Tkinter si PySide6 no esta disponible
│   └── main.py             # Despacho: GUI por defecto, --cli para status/install/update
├── build.sh / build.bat    # venv + instalación editable + compile-check
├── run.sh / run.bat        # GUI por defecto / entrada CLI
├── run-gui.vbs             # Lanzador grafico Windows sin ventana de consola
└── bump_version.py         # Incremento "cuentakilómetros" del ecosistema (pyproject.toml + __init__.py)
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
```

En Windows: `build.bat`, y luego `run.bat` (GUI) / `run.bat --cli status`
/ `run.bat --cli install <nombre>` / `run.bat --cli update <nombre>`.

La GUI preferida necesita el runtime Qt opcional (`pip install -e ".[gui]"`;
`build.bat`/`build.sh` ya lo instalan). `--cli` no tiene dependencia grafica y
es la entrada correcta para una CM5 headless. Si Qt no esta disponible, la
antigua ventana Tkinter es solo un fallback de compatibilidad.

**Solución de problemas**

- `status` muestra `?` en la versión local o de GitHub de un proyecto: su
  archivo de versión existe pero la convención de ese proyecto cambió
  desde la última actualización de `registry.py` - revisa la entrada de
  ese proyecto en `registry.py` contra su archivo de versión real actual.
- `status` muestra `-` en GitHub sin ningún error: ejecuta `status` (sin
  `--offline`) - `-` solo aparece cuando la comprobación de GitHub se
  omitió por completo.
- `install`/`update` falla con "No build.sh/.bat found": ese proyecto usa
  un nombre de script de build que esta herramienta aún no reconoce -
  revisa su propio README para ver el real, y considera añadirlo a las
  listas `BUILD_SCRIPT_CANDIDATES_*` propias de `install.py`.
- `git pull --ff-only` falla: el checkout local tiene cambios sin
  commitear o el historial ha divergido - resuélvelo a mano (`git
  status` dentro del propio directorio del proyecto) antes de reintentar
  `update`. Esta herramienta nunca fuerza un reset de un checkout.

## 🚀 HOJA DE RUTA

- Un ejecutable de GUI independiente empaquetado (PyInstaller, siguiendo
  la propia convención `build_exe.bat`/`.sh` de HYDRA-UMC-SUITE) para una
  instalación con doble clic sin ningún paso de `pip`/venv - hoy la GUI
  todavía necesita `./build.sh` primero, igual que la CLI.
- Comprobación previa opcional de dependencias por proyecto (avisar de
  toolchains faltantes - sin Rust/Go/SDK de Android/Flutter instalado -
  antes de que un `install` falle a mitad de camino).
- Un modo de salida `--json` para `status`, para poder scriptearlo.
- Seguimiento por componente para el firmware multi-binario propio de
  HYDRA-UMC/URTC (ver la "simplificación conocida" de la sección 3), en
  cuanto haya una necesidad real más allá del único componente
  representativo que se sigue hoy.

## 🔗 PROYECTOS RELACIONADOS

El propósito entero de esta herramienta es gestionar cada uno de los
demás proyectos del ecosistema - en vez de listar los 44 aquí (ver
`registry.py` para la lista exacta y autorizada), los dos más cercanos
en su papel:

- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - el
  controlador de célula multi-robot insignia que esta herramienta está
  pensada para mantener instalado y al día en el hardware CM5 real.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** -
  otra herramienta Python independiente pensada para correr junto al
  controlador de la célula, el hermano más cercano en su papel (una
  utilidad enfocada del lado de la CM5, no parte del propio camino de
  control de robots).

**Resto del ecosistema** (cada proyecto que esta herramienta puede
detectar/instalar/actualizar): los 12 proyectos originales (firmware,
servidores, apps móviles/de escritorio), los nodos de IA de
Visión/Cognitivos, los servicios de orquestación/simulación en Rust, las
herramientas de infraestructura/CLI en Go, las pasarelas industriales en
Node, y el firmware/herramientas de PC del cabezal de herramienta URTC -
ver la propia agrupación de `registry.py` (que coincide con los
comentarios de estructura de directorios de este mismo README) para la
lista completa y actual.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

GPL-3.0 (software) / CC BY-SA 4.0 (documentación) - ver [LICENSE.md](LICENSE.md).
