# =============================================================================
# HYDRA-UMC-UPDATER - QML Desktop GUI Guide
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================

# HYDRA-UMC-UPDATER QML desktop GUI

## Purpose

The desktop interface is a Qt Quick/QML control surface over the actual
HYDRA-UMC-UPDATER backend. It is not a static dashboard or a second update
implementation. Project discovery, GitHub checks and install/update operations
continue to use the same Python modules as `--cli`:

```text
QML Main.qml
    -> qt_gui.py / UpdaterBridge
        -> detect.py
        -> github_client.py
        -> install.py
```

This separation lets the presentation use animation, cards, colour states and
high-DPI graphics without duplicating any safety decision in QML.

## Runtime choices

- `--cli` remains stdlib-only and is the correct entry point on a headless CM5.
- The desktop mode uses the optional `PySide6` extra and starts automatically
  after `build.bat` or `build.sh`.
- On Windows, `run-gui.vbs` is the completely console-free desktop launcher:
  it starts the repository virtual environment's `pythonw.exe` directly.
  `run.bat` with no arguments delegates to it; `run.bat --cli ...` retains a
  visible terminal and `pause` deliberately for diagnostics.
- If the optional Qt runtime has not been installed yet, `main.py` temporarily
  starts the legacy Tkinter window instead. This fallback does not change
  command-line behaviour and can be removed only after the QML client has been
  proven on the intended CM5 desktop/VNC environment.

Install the visual runtime without an incremental version bump:

```bash
python -m pip install -e ".[gui]"
python -m hydra_umc_updater.main
```

For a normal complete local build use the existing `build.bat` or `build.sh`;
they install `.[dev,gui]` and then run the project tests.

## Real interface flow

| Area | Real data / action |
| --- | --- |
| Local Ecosystem | Workspace selector plus discovered, installed and outdated project counts. |
| Project Registry | `hydra-umc.project.json` data, grouped parent-first by family and filtered by deployment target. |
| Safe Update | Selected project, manual Install or Update operation, optional no-build mode, real checkpoints, animated progress and a bounded live activity trail. |
| Safety Gates | Existing manifest discovery, single-project action and explicit confirmation; the QML layer cannot bypass them. |

The coloured status in the registry is derived from the same local-versus-GitHub
version comparison used by the CLI. A green row is current, amber indicates an
ahead local checkout, red indicates an available update, and muted rows are not
installed or could not be checked.

The action buttons follow that same state model instead of merely checking
whether a row is selected: a missing checkout enables only **Install**; a
locally current/ahead checkout enables neither action; and **Update** is
enabled only when GitHub exposes a strictly higher valid version. This prevents
an ambiguous reinstall or a no-op update from being presented as an available
operation.

## Operator-confirmed batch actions

The normal action panel also offers two explicit batch actions:

- **Install all missing** selects every discovered manifest that has no local
  checkout under the chosen workspace. It therefore fills a partial local
  ecosystem without reinstalling repositories already present.
- **Update all outdated** selects only installed projects whose valid GitHub
  version is strictly greater than the valid local version.

Each batch opens its own confirmation dialog. It remains a human-triggered
operation, never a timer or automatic background update. Projects run one at a
time through the same clone/fetch, manifest validation, anti-rollback and
non-versioning `build-test` logic as a single action. A failure is recorded in
the in-window evidence and later independent projects continue, providing a
complete operator report without falsely declaring the whole batch successful.
The checkpoint heading identifies the current project and its position in the
approved batch.

## Real update evidence in the window

The update panel is not a cosmetic progress animation. An approved action
reports the actual sequence from `install.py` to the QML bridge:

1. **Preflight** validates the selected workspace and installed checkout.
2. **Source refresh** clones into a staging directory or fetches Git without
   changing the local checkout first.
3. **Manifest validation** checks the fetched candidate, including the
   anti-rollback rule, before a fast-forward-only merge can be applied.
4. **Build-test** runs that repository's own non-versioning build script, or
   is explicitly marked skipped when the operator selected source-only mode.
5. **Complete** is reached only after all approved steps succeed.

When launched graphically, Git and the selected `build-test` process have
their output captured without creating a second Windows command window. The
panel shows the last useful lines as bounded evidence; it never claims that an
install/update succeeded merely because the animation reached the end. A
failure marks the active checkpoint red and leaves the project untouched past
the failed safety gate.

The **About** button records the running updater version, licence, author and
Qt Quick runtime, and opens this repository on GitHub.

When an action begins, its checkpoint panel replaces the selected-project
card and action buttons in the same visual slot. Safety Gates and Activity Log
therefore retain their usable lower-panel space. The evidence remains after an
action completes; selecting another project restores the normal selected
project controls. The header uses `images/HYDRA_UMC_ICON.svg` at the original
54 px badge size rather than a text-only placeholder. (The SVG asset is used
directly; the available Qt SVG renderer determines whether its internal SVG
animation is rendered on a particular desktop runtime.)

For the operating-system window and Windows taskbar, `qt_gui.py` uses the
native `images/HYDRA_UMC_ICON.ico`. It is generated from that same SVG by
`tools/generate_app_icon.py`, so the source identity is never duplicated by
hand. Run it after intentionally changing the SVG asset.

## Visual design system

`qml/Main.qml` is intentionally a native QML scene rather than a themed
widget layout. It uses a deep navy background, cyan identity accents, status
colours, card elevation, hover transitions and an animated busy indicator. The
public real-interface captures are:

```text
images/HYDRA_UMC_UPDATER_INTERFACE_1.png  # overview and project states
images/HYDRA_UMC_UPDATER_INTERFACE_2.png  # completed update checkpoints
```

They document a real local session. Values shown by the application always
come from the live bridge, not from either image or from hard-coded sample
rows.

## QML validation

With the GUI extra installed, Qt's own linter is available:

```bash
pyside6-qmllint src/hydra_umc_updater/qml/Main.qml
```

The regular CI intentionally does not install the large desktop runtime just to
validate the command-line updater. Source compilation and the existing test
suite still run in CI; local GUI work additionally uses the QML linter and a
headless Qt smoke load.
