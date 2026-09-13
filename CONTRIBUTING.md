# Contributing to HYDRA-UMC-UPDATER 🦾

We welcome contributions to the fleet management tool of the HYDRA-UMC
platform.

## Technology Stack

- **Language**: Python 3.10+.
- **Dependencies**: stdlib only, deliberately - see `github_client.py`'s
  own header comment for why a tool responsible for keeping every OTHER
  discovered project's dependencies sane stays dependency-free itself.
- **Networking**: `urllib` (raw GitHub content fetches), never the
  GitHub Releases/tags API - see `github_client.py`'s own header comment
  for why that API would be wrong for this ecosystem's actual versioning
  convention.

## Guidelines

1. **Each `hydra-umc.project.json` is the source of truth** for its own
   metadata, version and native-version parser. Do not add a central project
   table: discovery must continue to work for a newly published manifest.
2. **One parsing implementation, not two** - `version_parse.py` is used
   identically by both a local file read (`detect.py`) and a GitHub fetch
   (`github_client.py`). Don't add a second regex implementation for
   either path.
3. **Never build per-stack logic here** - `install.py` delegates to each
   project's own `build.sh`/`.bat` (or a known equivalent) rather than
   reimplementing npm/cargo/go/gradlew/flutter/pip build steps. If a
   project's own build script is wrong, fix it there, not by working
   around it here.
4. **`install.py`'s own `install_or_update()` always takes one explicit
   project name** - the CLI (`hydra-umc-updater install/update PROJECT`)
   only ever calls it with a single project, and any new CLI subcommand
   should keep that same explicit, one-project shape (see `install.py`'s
   own header comment for why). The GUI's **Install all missing**/
   **Update all outdated** batch actions (`qt_gui.py`'s `performBatch()`)
   are the one deliberate exception, not a contradiction of this rule:
   they call this same `install_or_update()` once per project, in
   sequence, only after the operator explicitly confirms the whole
   batch - never a second, parallel implementation of the update logic
   itself. Do not add an unconfirmed "update everything" path anywhere,
   CLI or GUI.
