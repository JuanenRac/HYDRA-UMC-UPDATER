# Contributing to HYDRA-UMC-UPDATER 🦾

We welcome contributions to the fleet management tool of the HYDRA-UMC
platform.

## Technology Stack

- **Language**: Python 3.10+.
- **Dependencies**: stdlib only, deliberately - see `github_client.py`'s
  own header comment for why a tool responsible for keeping the OTHER 44
  projects' dependencies sane stays dependency-free itself.
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
4. **`install`/`update` always take one explicit project name** - there
   is no "update everything" command, and no PR should add one. See
   `install.py`'s own header comment for why that's a deliberate,
   non-optional design choice.
