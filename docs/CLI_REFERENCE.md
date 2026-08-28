# HYDRA-UMC-UPDATER — CLI Reference

`hydra-umc-updater` defaults to a windowed GUI. Passing `--cli` switches
to the headless argparse CLI documented here, before `tkinter` is ever
imported — the same pattern URTC-FLASHER's `--cli` fallback uses, so
`--cli` mode works on a genuinely headless CM5 with no `python3-tk`
installed and no display. Every example below was captured from a real
run of the installed CLI — not written from memory.

## Usage

```
$ hydra-umc-updater --cli -h
usage: hydra-umc-updater --cli [-h] [--version] {status,install,update} ...

Detects, installs, and manually updates the HYDRA-UMC/URTC ecosystem's
projects on this machine.

positional arguments:
  {status,install,update}
    status              Show what's installed, its version, and the latest
                        GitHub version of every project.
    install             Clone and build ONE project that isn't installed yet.
    update              Pull and rebuild ONE project that's already installed.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

```
$ hydra-umc-updater --cli --version
hydra-umc-updater 0.1.8
```

`install`/`update` are deliberately separate from `status` and always
take one explicit project name — there is no "update everything". A
fleet of real robots is not something to leave auto-updating
unattended: `status` shows what's outdated, a human picks what to
actually touch.

## Commands

### `status [--workspace PATH] [--offline] [--notes]`

```
$ hydra-umc-updater --cli status -h
usage: hydra-umc-updater --cli status [-h] [--workspace WORKSPACE] [--offline]
                                      [--notes]

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root to scan (default: this tool's own
                        parent directory).
  --offline             Skip the GitHub check - local state only.
  --notes               Also print each project's real notes (family/parent,
                        what's actually implemented, tech) below the table.
```

Scans `--workspace` (or this tool's own parent directory by default) for
sibling folders that expose a valid `hydra-umc.project.json` — a folder
name alone is never enough to join the ecosystem — and, unless
`--offline`, checks each one's real published version on GitHub too.

```
$ hydra-umc-updater --cli status --workspace /path/to/workspace --offline
Workspace root: /path/to/workspace
(--offline: not checking GitHub - showing local state only)
PROJECT         MATURITY     ROLE      STACK       LOCAL     GITHUB    STATE
----------------------------------------------------------------------------
DEMO-PROJECT-A  functional   service   python      1.2.3     -         installed (not checked)

1/1 installed, 0 outdated (GitHub not checked)
```

### `install <PROJECT-NAME> [--workspace PATH] [--no-build]`

```
$ hydra-umc-updater --cli install -h
usage: hydra-umc-updater --cli install [-h] [--workspace WORKSPACE]
                                       [--no-build]
                                       project

positional arguments:
  project               Exact project name (see `status` for the full list).

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root (default: this tool's own parent
                        directory).
  --no-build            Clone only - skip running the project's own build
                        script.
```

`git clone`s the named project into `--workspace`, then runs its own
`build-test.sh`/`.bat` unless `--no-build` is given. A project name that
doesn't expose a valid manifest on GitHub is a real, reported failure —
never a silent no-op:

```
$ hydra-umc-updater --cli install NOT-A-REAL-PROJECT
Unknown ecosystem project: 'NOT-A-REAL-PROJECT'
The project must expose a valid hydra-umc.project.json on GitHub.
$ echo $?
1
```

### `update <PROJECT-NAME> [--workspace PATH] [--no-build]`

```
$ hydra-umc-updater --cli update -h
usage: hydra-umc-updater --cli update [-h] [--workspace WORKSPACE]
                                      [--no-build]
                                      project

positional arguments:
  project               Exact project name (see `status` for the full list).

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root (default: this tool's own parent
                        directory).
  --no-build            Pull only - skip running the project's own build
                        script.
```

`git pull --ff-only` on an already-installed project's checkout, then
runs its own build script unless `--no-build` is given. `--ff-only` is
deliberate and load-bearing: **a healthy local checkout is never
replaced**. A real local edit (this tool is meant to also run on a
developer machine, not only the CM5) or a diverged branch makes the
pull fail loudly with git's own error — never a silent reset or a
discarded change:

```
$ cd /path/to/workspace/SOME-PROJECT && git log --oneline -1
a1b2c3d local work in progress
$ hydra-umc-updater --cli update SOME-PROJECT
Pulled latest into ... failed (exit 1) - local changes or a diverged branch?
$ cd /path/to/workspace/SOME-PROJECT && git log --oneline -1
a1b2c3d local work in progress   # unchanged
```

(Exercised for real in `tests/test_install.py`'s
`test_diverged_pull_fails_without_resetting_local_checkout`: a real
diverged git history is built, `pull --ff-only` is proven to fail, and
`HEAD`/file content are proven byte-for-byte unchanged afterward.)

## Exit codes

`status` always exits `0` (even when projects are outdated — that's
informational, not a failure). `install`/`update` exit `1` on any real
failure (unknown project, failed clone/pull, failed build script) and
`0` on success.

## Network resilience

Every real GitHub request `status` makes (repository listing, manifest
fetch) retries up to 3 times with backoff for a genuinely transient
network failure (DNS/timeout/connection reset) before giving up — never
for a definitive HTTP response GitHub already returned (404/403/500). If
the remote catalog itself is unreachable or malformed, `status` falls
back to local-only state with a `WARNING:` line instead of crashing.

## GUI

Running `hydra-umc-updater` with no arguments (or double-clicking it)
opens a windowed GUI instead — a sortable, filterable project table with
Install/Update buttons for whichever row is selected, and a language
selector (7 languages; the CLI itself stays English-only, since it's
meant to be scripted/piped).
