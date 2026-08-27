<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-UPDATER banner" width="100%">
</p>

# 🛠️ HYDRA-UMC-UPDATER

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 📦 Detect, Install, and Manually Update the Whole HYDRA-UMC/URTC Ecosystem

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.10%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Dependencies-stdlib%20only-brightgreen.svg" alt="stdlib only">
</p>

---

## 1. 🛠️ TECHNICAL OVERVIEW

HYDRA-UMC-UPDATER is a small tool - windowed GUI by default, full CLI with
`--cli` - meant to run either on the real CM5 itself or on a developer's
own Windows/Linux/macOS machine (any workspace checked out the same way)
that answers three questions for every one of the ecosystem's 44 other
projects:

1. **What's actually installed here, and what version is it?**
2. **What's the latest version published on GitHub?**
3. **If GitHub is newer, let me update THAT ONE PROJECT, by hand.**

That last point is deliberate and non-negotiable: this tool never updates
more than one project per command, and never on its own initiative. A
robot-control cell is not something you want auto-updating itself
overnight - every real update is a command (or a button click, for one
row selected in the GUI's table) a person triggered, for one named
project, whose result they can see before touching the next one.

Not every one of the 44 projects belongs on the CM5 itself, either - most
URTC-prefixed repos and a few HYDRA-UMC ones are tools a developer runs
from their own PC (firmware gets compiled/flashed FROM a workstation, not
built ON the cell) or apps installed on a phone/watch. `registry.py`'s own
`deploy` field records which is which (see section 3), and the GUI's
project table filters by it - defaulting to "CM5 only" when it detects
it's running on Linux (the real CM5's own OS), and "show everything" on
Windows/macOS.

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

Running `hydra-umc-updater` with no arguments (or double-clicking it)
opens the same information in a window instead - a sortable project
table, a deploy-target filter, and Install/Update buttons for whichever
row is selected.

## 2. 🔄 HOW A CHECK/UPDATE ACTUALLY WORKS

- **Version source**: this ecosystem's own "odometer" auto-bump
  convention (every real build increments a version number that lives
  IN a source file - `pyproject.toml`, `Cargo.toml`, `version.go`,
  `package.json`, `version.properties`, `pubspec.yaml`, or a firmware
  `#define`, depending on the project's stack) has never created a git
  tag or a GitHub Release for that bump. So this tool reads the SAME
  file every project's own `bump_version.py`/build script already
  writes, straight off the repo's default branch via GitHub's raw
  content host - not the Releases API, which would report every project
  as having no releases at all.
- **Local detection**: for each of the 44 known projects, checks whether
  a directory with that exact name exists under the workspace root (the
  standard ecosystem layout - every project as a sibling directory,
  exactly what `build-frontend.sh`/HYDRA-UMC-SUITE's own discovery
  already assume), and if so, reads its OWN local copy of that same
  version file.
- **One parsing implementation** (`version_parse.py`) is shared between
  the local read and the GitHub fetch, so a local checkout and a GitHub
  fetch are never interpreted by two independently-drifting regexes.
- **Install/update**: `git clone` (install) or `git pull --ff-only`
  (update - never a force-reset, so real local edits fail loudly instead
  of being discarded), then runs whichever of that project's own
  `build.sh`/`build.bat` (or a known equivalent - see section 3) it
  actually has. This tool never reimplements a project's own build
  steps - see section 3 for why.

## 3. 🧱 ARCHITECTURE & DESIGN DECISIONS

- **Windowed GUI by default, `--cli` for headless.** Tkinter/ttk (stdlib,
  no new dependency) - the same GUI toolkit and dual-entry-point pattern
  `URTC-FLASHER`/`URTC-TESTER` already use in this ecosystem: `main.py`
  checks `sys.argv` for `--cli` **before** ever importing `tkinter`, so
  `--cli` mode works on a genuinely headless CM5 with no `python3-tk`
  installed and no display, while bare invocation gets the friendlier
  windowed experience everywhere else (including a CM5 with a local
  desktop/VNC session, and a developer's own PC).
- **The windowed GUI is real, 7-language multilingual (`i18n.py`) - `--cli` deliberately isn't.** Every real widget re-labels live from a language `Combobox` (en/es/fr/it/de/zh/ja, the same 7 the public dashboard and every README ship), detected from a saved preference or the OS's own locale. Project/family names and each project's own real `notes`/`tech` text stay untranslated - `registry.py` is their one source of truth, and 7 parallel copies of real engineering documentation would stop it being that. `--cli` output stays English-only on purpose: it's meant to be scripted/piped, where stable, greppable text matters more than localization.
- **`deploy` is a classification, not a restriction.** Treating all 44
  projects as "things that belong on the CM5" was wrong - firmware repos
  are compiled and flashed FROM a PC (the CM5 only ever needs the
  resulting binary over CAN-OTA, never this repo's own source), and
  several tools (URTC-FLASHER, HYDRA-UMC-SUITE, HYDRA-UMC-TOOL-CLI, ...)
  are meant to run on an operator's own workstation, not inside the cell
  itself. `registry.py`'s `deploy` field ("cm5" / "user-pc" / "mobile" /
  "wearable") records that, and the GUI's filter uses it as a sensible
  starting point - never a hard restriction, since this same tool is also
  meant to run on a developer's own PC where every one of the 44 is fair
  game to inspect.
- **No per-stack build logic in this tool.** The ecosystem spans 7
  toolchains (Python, Rust, Go, Node/TS, Android/Kotlin, Flutter, ARM
  firmware). Reimplementing `npm install && npm run build` /
  `cargo build --release` / `./gradlew assembleDebug` / etc. HERE would
  create a second place that claims to know how to build each project,
  guaranteed to drift from that project's own real (and already correct)
  `build.sh`/`.bat`. `install.py` instead probes for a known build-script
  name (`build.sh`, `build_firmware.sh`, `build_exe.sh`,
  `build-android.sh`, and their `.bat` equivalents - the real names used
  across the 44 projects) and runs whichever one exists.
- **GitHub raw content, not the Releases API.** See section 2 above -
  this ecosystem's versioning convention never creates a tag/release, so
  the Releases API would be actively wrong here, not just less
  convenient.
- **`install`/`update` always take one explicit project name.** There is
  no "update everything" subcommand, and this is a design decision, not
  a missing feature - a fleet of real robots is not something to leave
  auto-updating unattended. `status` shows what's outdated; a human picks
  which one to actually touch.
- **stdlib only.** `urllib` for the GitHub fetches (`github_client.py`),
  `subprocess` for git/build-script calls (`install.py`), nothing else -
  a tool responsible for keeping every OTHER project's dependencies sane
  staying dependency-free itself is deliberate.
- **Known simplification**: HYDRA-UMC and URTC are real multi-component
  firmware repos (6 and 4 independently-versioned binaries each - see
  their own `VERSION_CHECKLIST.txt`/`build_firmware.sh`) with no single
  "the" version number. `registry.py` tracks ONE representative
  component per repo - good enough to answer "is this repo roughly up to
  date", not a replacement for `build_firmware.sh`'s own
  `firmware_manifest.json` for a real flash.

## 📂 DIRECTORY STRUCTURE

```
HYDRA-UMC-UPDATER/
├── src/hydra_umc_updater/
│   ├── registry.py        # The 44 projects: repo, stack, version file, pattern, deploy target
│   ├── version_parse.py   # ONE regex-extraction implementation, local+GitHub
│   ├── detect.py          # Scans a workspace root for what's installed
│   ├── github_client.py   # Concurrent raw-content fetch of GitHub's latest version
│   ├── install.py         # git clone/pull + delegate to the project's own build script
│   ├── gui.py              # Windowed GUI (Tkinter/ttk) - the default entry point
│   └── main.py             # Dispatch: GUI by default, --cli for status/install/update
├── build.sh / build.bat    # venv + editable install + compile-check
├── run.sh / run.bat        # Runs the tool (forwards all arguments - see USAGE below)
└── bump_version.py         # Ecosystem-wide odometer bump (pyproject.toml + __init__.py)
```

## ⚙️ BUILD & RUN

```bash
chmod +x build.sh   # one-time
./build.sh          # creates .venv, pip install -e ., compile-checks everything
./run.sh                              # windowed GUI (default)
./run.sh --cli status                 # what's installed, local vs. GitHub version
./run.sh --cli status --offline       # same, skipping the GitHub check
./run.sh --cli install <PROJECT-NAME> # clone + build one project not yet installed
./run.sh --cli update  <PROJECT-NAME> # pull + rebuild one project already installed
```

On Windows: `build.bat`, then `run.bat` (GUI) / `run.bat --cli status` /
`run.bat --cli install <name>` / `run.bat --cli update <name>`.

The GUI needs `python3-tk` on a from-source Linux Python (Debian/Raspberry
Pi OS: `sudo apt install python3-tk`) - bundled already with the
python.org Windows/macOS installers. Without it, bare invocation prints a
short notice and falls back to `--cli`'s own help text rather than
crashing.

**Troubleshooting**

- `status` shows `?` for a project's local or GitHub version: its version
  file exists but this project's own convention changed since
  `registry.py` was last updated - check `registry.py`'s entry for that
  project against its real, current version file.
- `status` shows `-` for GitHub with no error shown: run `status`
  (without `--offline`) - `-` only appears when the GitHub check was
  skipped entirely.
- `install`/`update` fails with "No build.sh/.bat found": that project
  uses a build script name this tool doesn't recognize yet - check its
  own README for the real one, and consider adding it to
  `install.py`'s own `BUILD_SCRIPT_CANDIDATES_*` lists.
- `git pull --ff-only` fails: the local checkout has uncommitted changes
  or diverged history - resolve that manually (`git status` in that
  project's own directory) before retrying `update`. This tool never
  force-resets a checkout.

## 🚀 ROADMAP

- A packaged standalone GUI executable (PyInstaller, matching
  HYDRA-UMC-SUITE's own `build_exe.bat`/`.sh` convention) for a
  double-click install with no `pip`/venv step at all - today's GUI still
  needs `./build.sh` first like the CLI does.
- Optional per-project dependency preflight (report missing toolchains -
  no Rust/Go/Android SDK/Flutter installed - before an `install` fails
  partway through).
- A `--json` output mode for `status`, for scripting against it.
- Per-component tracking for HYDRA-UMC/URTC's own multi-binary firmware
  (see the "known simplification" in section 3), once there's a real
  need beyond the single representative component this tracks today.

## 🔗 RELATED PROJECTS

This tool's whole purpose is managing every other project in the
ecosystem - rather than listing all 44 here (see `registry.py` for the
authoritative, exact list), the two closest in role:

- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** - the flagship
  multi-robot cell controller this tool is meant to keep installed and
  current on the real CM5 hardware.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** -
  another standalone Python tool meant to run alongside the cell
  controller, closest sibling in role (a focused CM5-side utility, not
  part of the robot-control path itself).

**Rest of the ecosystem** (every project this tool can detect/install/
update): the 12 original projects (firmware, servers, mobile/desktop
apps), the Vision/Cognitive AI nodes, the Rust orchestration/simulation
services, the Go infrastructure/CLI tools, the Node industrial gateways,
and the URTC tool-head firmware/PC tools - see `registry.py`'s own
grouping (matching this README's own directory-structure comments) for
the complete, current list.

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)**
Email: electrohobby3d@gmail.com
YouTube: [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

GPL-3.0 (software) / CC BY-SA 4.0 (documentation) - see [LICENSE.md](LICENSE.md).

## 🛠️ BUILD & RUN

Use the non-versioning build check before a release build:

| Action | Windows | Linux / macOS |
|---|---|---|
| Build check (no version or CHANGELOG change) | `build-test.bat` | `./build-test.sh` |
| Run / development (when provided) | `run*.bat` or `dev*.bat` | `./run*.sh` or `./dev*.sh` |

`build-test.bat` and `build-test.sh` compile or validate the project stack without incrementing `hydra-umc.project.json` or modifying `CHANGELOG.md`. They may create normal compiler output only. Existing `build*.bat`, `build*.sh`, `run*` and `dev*` scripts retain their project-specific, versioned or runtime behavior; use them when that behavior is required.

> **Updater safety:** automatic install and update run only build-test, never a versioned build. Release builds remain an explicit human action.
