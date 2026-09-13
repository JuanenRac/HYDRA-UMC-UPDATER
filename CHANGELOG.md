# Changelog: HYDRA-UMC-UPDATER 🛠️

All notable changes to this project will be documented in this file. The
version number follows this ecosystem's "odometer" scheme: PATCH +1 on
every real build, rolling into MINOR past 9 (`0.0.9` -> `0.1.0`); MAJOR is
bumped manually only. See `bump_version.py`.

## Unreleased

(nothing yet)

## [0.3.6] - P01/I13: a real post-promotion health check, wired into every promotion that declares one

I13 ("Checkpoints respaldados por postcondiciones"): finishing the 2
promotion renames is not the same as a HEALTHY promotion - the real
postcondition is "servicio comprobado" (service checked), not merely
"files moved". `install.py` now builds a real
`http://127.0.0.1:<service_port><service_health_path>` target
(`_health_check_url_for()`) whenever a project's own manifest declares
BOTH fields, passes it into the durable journal (HYDRA-UMC-SDK's new
`check_service_health()`, see that project's own 0.1.9), and only
reports the promotion a real success once that endpoint genuinely
answers 2xx - a 4xx/5xx (the freshly-promoted code IS running, but is
not well) is treated as a real failure, not waved through. A project
declaring neither field behaves exactly as before this feature existed.

If the process crashes between promoting and checking, the durable
journal already recorded the health-check target before either
happened - `recover_interrupted_promotions()` now runs that pending
check for real on the next start (never repeating the clone/build), and
still refuses to mark the promotion complete until it genuinely passes.
This is I13's own literal acceptance test: cut the process after
promoting and before checking health, restart, and the pending check
runs for real rather than announcing success prematurely.

2 new tests (`test_install.py`): a real local HTTP server answering 200
completes the promotion end to end, and a real closed port leaves the
promotion honestly reported as failed AND still pending in the journal
(the checkout itself really was promoted - only its health is in
question).

Verified: 70/70 tests, `ci_validate.py` PASS.

## [0.3.5] - P01: an optional durable promotion journal, wired into every real promotion

V07-004's own real, bounded mitigation (this project's in-process
self-heal for the narrow gap between clone_or_pull's own 2 promotion
renames) already named the real remaining gap: "not the full
transactional journal/rollback... that needs designing once, shared
with HYDRA-UMC-OPS-AGENT's own canary_deploy.py". HYDRA-UMC-SDK now
ships that shared journal (`promotion_journal.py`) - this wires it in.

`install.py` imports `hydra_umc_sdk.promotion_journal` inside a
try/except at module load, mirroring the SAME optional-extra shape
this project's own PySide6 GUI dependency already established (see the
new `durable-journal` entry in `pyproject.toml`'s
`[project.optional-dependencies]`): the safety-critical update core
stays usable with zero external dependencies when it isn't installed -
`clone_or_pull()`'s own existing in-process self-heal is completely
unchanged either way. When it IS installed, a `PromotionRecord` is
written to disk (atomically) before the first real rename, advanced as
each rename succeeds, and completed on success - so a promotion
interrupted by a full process crash, `kill -9`, power loss, or a reboot
(not just an in-process exception) is recoverable. New
`recover_interrupted_promotions()`, called automatically at the start
of `install_or_update()` (every real entry point - CLI, Tkinter GUI, Qt
GUI - funnels through it) - a genuine no-op when nothing was pending or
when the SDK isn't installed.

4 new tests (`test_install.py`): the real no-SDK no-op default, a full
real promotion through `clone_or_pull()` with the SDK importable
leaving nothing pending in the journal, a real crash simulation healed
by `recover_interrupted_promotions()`, and confirmation
`install_or_update()` actually calls recovery before its own work.

Verified: 68/68 tests (run against this repo's own `.venv` specifically -
a stray, unrelated venv happening to be active on the shell can shadow
this project's own package with an older installed copy, silently
hiding real new test failures/passes), ci_validate PASS 0.3.5.

## [0.3.4] - Recognize the optional `deployment_target_note` manifest field

Real regression found while regenerating JuanenRac's own dashboard:
`HYDRA-UMC-DEV-SERVER`'s manifest was being rejected outright -
`unknown field(s): deployment_target_note` - excluding it completely
from both this project's own discovery/status tooling and the public
dashboard, not just from the new deployment_target value (0.3.3 already
fixed that half).

- `src/hydra_umc_updater/project_manifest.py` - `"deployment_target_note"`
  added to `optional_fields` (a real, human-readable clarification for a
  deployment_target value whose meaning isn't self-evident from the enum
  alone - optional because most values need no such note). New test
  `test_accepts_the_optional_deployment_target_note_field`, reproducing
  the exact real failure against DEV-SERVER's own live manifest before
  confirming the fix.

## [0.3.3] - Recognize the new `dev-server` deployment_target

`HYDRA-UMC-DEV-SERVER`'s own manifest declares `deployment_target:
"dev-server"` - this project's `VALID_DEPLOYMENT_TARGETS` only allowed
`cm5`/`user-pc`/`mobile`/`wearable`, so its manifest would have been
rejected outright by `validate_project_manifests.py`/
`migrate_project_manifests.py`.

- `src/hydra_umc_updater/project_manifest.py` - `"dev-server"` added to
  `VALID_DEPLOYMENT_TARGETS`. New tests
  `test_accepts_dev_server_deployment_target` and
  `test_rejects_an_unsupported_deployment_target` (the latter didn't
  exist for any deployment_target value before).
- `src/hydra_umc_updater/gui.py` and `qt_gui.py` - `"dev-server"` added
  to both GUIs' own `DEPLOY_ORDER` (Tkinter combo box and the QML
  `deployOptions` property respectively).
- `src/hydra_umc_updater/i18n.py` - `"deploy_dev-server"` added to all 7
  language blocks (en/es/fr/it/de/zh/ja) - `test_i18n.py`'s own
  every-language-same-keys test enforces this stays complete.
- README + 6 translations - the `deploy` field's own documented value
  list now includes `dev-server`.

## [0.3.2] - V07-004: promotion could destroy its own only recovery point

Found in a review pass (P1), shared with
HYDRA-UMC-OPS-AGENT's own `canary_deploy.py` (same real gap, same real
fix - a full transactional journal/rollback across both implementations
stays real, separate future work, not claimed as done here):

- **The previous installation's own backup used a single fixed path**
  (`<name>.backup`), `rmtree`'d and overwritten on every promotion. A
  second real update after a first one already succeeded silently
  destroyed the ONLY other recoverable copy, with no way back to
  either release. Now unique per attempt (`<name>.backup-<uuid>`),
  matching OPS-AGENT's own fix - never overwrites an earlier backup.
- **A crash or exception in the narrow gap between the two promotion
  renames used to leave NO active checkout at `path` at all** - the
  single worst outcome this function's own docstring warned about but
  never actually handled. Now a best-effort self-heal: if the second
  rename (staging clone into place) fails, immediately try to rename
  the backup back so a real installation still exists, with a result
  message that distinguishes "restored" from "restore also failed."

New `test_two_successive_updates_never_overwrite_the_earlier_backup` and
`test_promotion_self_heals_when_the_second_rename_fails` in
`tests/test_install.py` (a real, injected `Path.rename` failure on
exactly the second promotion rename, nothing else) - 61/61 tests pass.

## [0.3.1] - V07-001: a real tracked-file edit could still be silently discarded

- **`clone_or_pull()`'s own docstring claimed** "a real local edit... fails
  loudly... instead of being silently discarded" - true only for the
  older `verify_build=False` in-place `git merge --ff-only` path.
  Found in a review pass (P1, a real gap the
  REV-002 fix didn't close): once `verify_build=True` (the default)
  moved to building in an isolated staging clone, that claim silently
  stopped being true. `git clone --local` only ever copies the
  COMMITTED object database - a genuine uncommitted edit to an
  already-tracked file lives only in the installed checkout's own
  working tree, invisible to the fresh staging clone. Its own `git
  merge --ff-only` therefore always succeeds, the build succeeds, and
  promotion renames the dirty original aside to `.backup` - the real
  edit survived only there, while `clone_or_pull()` still reported
  `ok=True`.
- **Fixed**: new `_tracked_dirty_paths()` checks upfront, before any
  fetch/staging work, whether the installed checkout has a real
  uncommitted change to a tracked file (`git status --porcelain`'s own
  codes other than `??`/`!!`, which `_real_untracked_paths()` already
  owns) - if so, the update is refused outright with the exact file(s)
  named, before anything is touched. Applies to both `verify_build`
  values.
- New `test_update_refuses_when_a_real_tracked_file_has_an_uncommitted_edit`
  reproduces an explicit exact scenario against real temporary Git
  repositories (a bare remote, a seed clone, and an "installed"
  checkout) - confirmed failing against the pre-fix code (`ok=True`,
  edit silently lost to `.backup`), now passing. Full suite:
  `PYTHONPATH=src python -m pytest tests -q` - 59 passed (was 58).
  `tools/ci_validate.py` PASS.

## [0.3.0] - REV-001/REV-002: real regressions found by independent revalidation, plus prior unreleased work

A review pass reproduced 2 real regressions in
UPD-01's own staging-clone update path (each against a real local git
remote/checkout, no mocked git). Both fixed here, each with new
regression tests:

- **REV-001 [P1]:** `git clone --local` (used to build the staging
  clone) points the new clone's own `origin` remote at the LOCAL SOURCE
  PATH it was cloned from - never this project's real GitHub upstream.
  Left uncorrected, the checkout that staging clone becomes once
  promoted ends up with `origin` pointing at itself, so every FUTURE
  `git fetch origin` fetches nothing new - silently and permanently
  stopping that checkout from ever discovering a real update again after
  its first verified-build update. Fixed: the staging clone's `origin`
  is reset to the real upstream (`github_repo_url()`) immediately after
  it is created, before build or promotion.
- **REV-002 [P1]:** `git clone --local` only ever copies the committed
  object database - a project's own real local data living untracked
  inside its checkout (`data/settings.json`, `data/users.json`, a real
  sqlite file, generated TLS material, ...) was left behind entirely
  once the old installation was renamed aside to `.backup`, a real,
  silent data loss on every update of a project that keeps any real
  local state inside its own checkout - which describes most services
  in this ecosystem. Fixed: every real file/directory the installed
  checkout's own `git status --ignored` reports as untracked or ignored
  is now copied into the staging clone before it is built, with a
  denylist (`node_modules`, `dist`, `.venv`, `__pycache__`, ...) so a
  regenerable build artifact is never carried over.
- 2 new regression tests, both passing after the fix and confirmed to
  fail against the pre-fix code.

Also includes prior unreleased work:

- **`github_client.py` distinguishes a real GitHub rate limit from any
  other HTTP error** (new `describe_http_error()`/`_retry_after_seconds()`)
  - found while auditing the code: every
  `HTTPError` used to become the same opaque `"HTTP {code}"`, including a
  GitHub 403/429 primary rate limit, which carries a real
  `X-RateLimit-Reset` and is genuinely transient - a real failure mode
  running status/discovery across 55+ repos without a `GITHUB_TOKEN`
  (unauthenticated calls are capped at 60/hour). The message now surfaces
  the real reset time and points at `GITHUB_TOKEN`. A separate, short-lived
  secondary rate limit (403/429 with a real `Retry-After` header) is now
  actually retried within `_urlopen_with_retries` - the hourly primary
  limit still isn't, since it can be tens of minutes away and isn't worth
  blocking a foreground run for. New regression tests for both paths.
- **Real UI sizing pass, per real user feedback**: About and Copy (Activity
  Log) are now double width; Refresh is 50% wider; the About dialog's own
  Close button is now double width and its Open on GitHub button is 25%
  wider. All widths measured from the real current implicit sizes, not
  guessed. The other, unrelated "Open on GitHub" button (opens a selected
  project's own GitHub page) is untouched.

## [0.2.9] - Updating an existing checkout is now atomic-by-verification (UPD-01)

Found while auditing the code, P1:

- **The bug.** Updating an existing checkout merged the candidate
  straight into the live installation with `git merge --ff-only`, then
  left building it to a later, separate step. A build failure there left
  the NEW source merged in right next to the PREVIOUS build's artifacts
  - an inconsistent install with no rollback - and the on-disk manifest
  version never actually proved the installed executable matched it.
- **The fix.** `clone_or_pull` now clones the installed checkout into a
  fully independent staging clone, fast-forward-merges the fetched
  candidate there, and builds/verifies it - all before the live
  installation is touched at all. Only if that staging build succeeds
  does promotion happen, via two back-to-back directory renames (each
  individually atomic on the same filesystem): the previous installation
  is renamed to `<name>.backup` (kept, never deleted - an operator can
  restore it by hand if the new version misbehaves despite building
  fine) and the proven-buildable staging clone is renamed into the live
  path. A build failure, a diverged/dirty checkout, a crash, or a full
  disk at any point before that final promotion leaves the previous
  installation completely untouched and still operative. The success
  message now names the real commit SHA that was verified-built, not
  just the manifest's own version string. `verify_build=False` (used
  when the caller explicitly skips the build step) restores the exact
  previous in-place-merge behavior.
- **Real Windows finding, fixed in the implementation itself, not just
  papered over in tests:** a plain `git clone --local` hardlinks object
  files from the source repo by default - reproducible testing found
  that running a build script inside a hardlinked staging clone can
  leave those objects genuinely undeletable afterward on Windows
  (`WinError 5`, not a transient lock - retrying does not help), which
  would have silently left an orphaned staging directory behind forever
  on a failed build. The staging clone now uses `--no-hardlinks`.
- 3 new tests: a successful update (confirms promotion, the backup, and
  that the STAGING build's own artifacts - not a second build - land in
  the promoted checkout), a build failure (confirms the previous
  installation is completely untouched and still builds), and
  `verify_build=False` (confirms the old in-place-merge behavior is
  unchanged for a caller that wants it).

Verified with `pytest tests/` (56/56 PASS, the exact command this
repo's own test suite is run with).

## [0.2.8] - Real family-tree bug fix (v4 manifest-discovery era)

- **Real user feedback (same 3 fixes as HYDRA-UMC-OS-REBUILDER's own
  identical pass): the GUI window now opens maximized
  (`visibility: Window.Maximized`), the Activity Log is now real,
  selectable/copyable text (a `TextArea` in a `ScrollView`, plus a real
  "Copy" button) instead of an unselectable `ListView`, and every real
  activity line - not just the last 8 the visible strip shows - now
  also lands in a real plain-text log file
  (`~/.hydra_umc_updater/logs/gui_<timestamp>.log`), shown under the
  log panel. New `UpdaterBridge.fullActivity` (the same real data as
  `activity`, unbounded) backs the new view; `activity` itself is
  unchanged. Verified live: the file is created and receives real log
  lines (including a real 56-project GitHub scan) on a real launch.
- **New `--cli status --json`**, for scripting - the same real local+
  remote discovery `status` already does, as a real JSON object
  (`projects[]` with name/maturity/role/stack/installed/path/
  local_version/github_version/state, plus installed_count/
  outdated_count/total). Real bug fixed in the same pass: `cmd_status()`
  printed `"Workspace root: ..."` (and, with `--offline`, a second plain
  line) to stdout unconditionally, ahead of the table - with `--json`
  that broke the exact machine-readability the flag promises, since
  those lines landed before the JSON object itself. Both are now gated
  on `not args.json`. New `tests/test_main.py` (this repo's first CLI
  test file) exercises the real JSON shape against monkeypatched local/
  remote discovery. Verified live against the real ecosystem too.
- **More developed About dialog**, matching HYDRA-UMC-STUDIO's own
  `About.tsx`: the placeholder "H" letter box is now the real animated
  `VectorImage` mark (same source/renderer as the main header), the
  title is a colored HYDRA-UM-C wordmark, and Version/Author/Email/
  License are now real structured rows (email opens a `mailto:` link)
  instead of two plain copyright/license text lines. New `about_tagline`/
  `about_version_label`/`about_author_label`/`about_email_label`/
  `about_license_label` keys across all 7 languages; `about_license`'s
  value expanded from the bare string "GPL-3.0" to the full license name.
- **Fixed `--cli status`'s STACK column running into LOCAL with no space**:
  the column used a fixed 12-char width, silently fine while every real
  `stack` value stayed under it - the moment a real manifest recorded the
  14-char `python-qtquick`, it printed straight into the next column
  (`python-qtquick0.0.2`). Now sized dynamically from the real data, same
  approach already used for the PROJECT column.
- **In-window real update checkpoints**: the Qt Quick Safe Update panel now
  presents Preflight, Source refresh, Manifest validation, Build-test and
  Complete with a real progress bar. These states are emitted by the existing
  `install.py` clone/fetch/validation/build workflow; they are not a simulated
  animation. GUI-launched Git/build child output is captured as bounded
  in-window evidence and a failed command marks the actual active checkpoint
  red rather than reporting a false completion.
- **Console-free graphical launch on Windows**: added `run-gui.vbs`, which
  launches the local virtual environment's `pythonw.exe` without a Command
  Prompt. Bare `run.bat` delegates to it; `run.bat --cli ...` deliberately
  preserves the terminal and pause used for diagnostics.
- **Qt Quick About panel**: the visual client again exposes author, licence,
  running version, desktop runtime and a direct repository link.
- **State-aware action panel**: the visual client now enables Install only
  for a missing checkout, enables Update only for a strictly newer GitHub
  version, and disables both for current/ahead local installations. During an
  approved operation the selected-project controls are replaced by the real
  checkpoint panel; selecting another project after completion restores the
  normal controls without sacrificing Safety Gates or Activity Log space.
- Replaced the text-only header H badge with the existing
  `images/HYDRA_UMC_ICON.svg`, kept at the original 54 px visual size, and
  aligned About to the upper-right header edge.
- **Native application icon**: generated `images/HYDRA_UMC_ICON.ico` from
  the official SVG and assigned it through Qt to the window/taskbar. Added the
  reproducible `tools/generate_app_icon.py` generator rather than maintaining
  an independently drawn binary icon.
- **Animated in-window identity**: the Qt Quick header now uses `VectorImage`
  for the official SVG and loops its supported transform animation. The native
  taskbar/window ICO remains intentionally static, as required by that OS icon
  surface.
- **Real README evidence**: replaced the obsolete conceptual preview reference
  with operator-captured `HYDRA_UMC_UPDATER_INTERFACE_1.png` (overview) and
  `HYDRA_UMC_UPDATER_INTERFACE_2.png` (completed checkpoints) in every public
  README language.
- **Documentation image placement**: the overview capture now appears after
  the desktop-interface explanation, while the checkpoint capture appears
  directly after the documented install/update flow in every README language.
- **Operator-confirmed batch maintenance**: the visual client now offers
  Install all missing and Update all outdated. Both calculate their target set
  from the live discovered local/remote state, require a separate confirmation,
  run sequentially through the existing safe per-project path, show the
  current project in checkpoints and report failures without silently stopping
  the independent later targets.

- **Qt Quick/QML desktop migration**: the preferred window is now a real
  PySide6 QML client (`qt_gui.py` + `qml/Main.qml`), not a recoloured Tk
  layout. It presents local workspace metrics, the manifest-backed project
  registry, explicit single-project Install/Update actions, visual safety
  gates and the activity trail in one animated desktop control surface.
- **One backend, two entry points**: QML calls the existing
  `discover_workspace`, `discover_remote_projects`, `fetch_all` and
  `install_or_update` services. The headless `--cli` entry point remains
  stdlib-only; a legacy Tkinter shell remains as a temporary compatibility
  fallback if the optional `PySide6` runtime is not installed.
- Added `docs/QML_DESKTOP_GUI.md`, including the real QML/Python boundary,
  visual runtime installation, safety flow and Qt linter command.
- **Second visual pass**: replaced the remaining platform-default Qt buttons,
  combo boxes and check boxes with themed QML controls. Their backgrounds,
  borders, pressed/hover states and foreground text are now explicit, avoiding
  unreadable dark platform text over the updater's dark control surface. The
  desktop typography is larger and uses a technical system-font preference
  with platform fallback instead of the small default widget font.

- **Dark desktop updater control surface**: redesigned the real Tkinter GUI
  around the documented three-panel updater workflow, rather than adding a
  separate mock screen. The left panel exposes the selected workspace and
  live project/install/update counts; the centre remains the real
  manifest-driven family tree; the right panel keeps the selected project,
  explicit Install/Update actions, safety gates and an on-screen activity
  trail together. Existing discovery, GitHub verification, confirmation and
  build flows are unchanged.
- Added `images/HYDRA_UMC_UPDATER_INTERFACE_PREVIEW.png`, a public visual
  reference for the real interface, and linked it from every README language.

- **Runtime version-mirror regression**: `pyproject.toml` and the project
  manifest correctly declared `0.2.2`, but the runtime `__version__` mirror
  had remained at `0.2.1`. It is now synchronized, and a test reads both
  source files on every test run so a future build cannot silently reintroduce
  this mismatch.
- **Clone staging and rollback coverage**: a clone now lands in a unique
  sibling staging directory and is renamed into place only after Git succeeds.
  Failed clones leave no partial installation; a real local Git divergence
  fixture proves `pull --ff-only` preserves the operator checkout unchanged.
- **Real bug found and fixed via live GUI testing**: `gui.py::_render_rows()` builds the parent/child Treeview in a single insertion pass that requires a project's parent to already be inserted (`parent_iid = entry.parent if (entry.parent and entry.parent in inserted) else ""`), on the assumption - stated in the code's own comment - that discovery sorts each family's parent before its children. That assumption broke once `detect.py::discover_workspace()` moved to dynamic, manifest-driven discovery: it only sorts alphabetically by folder name, which is frequently NOT parent-before-children (e.g. `HYDRA-UMC-ANDROID-CONTROL` sorts before its own parent `HYDRA-UMC-SERVER`). Real impact: 4 of `HYDRA-UMC-SERVER`'s 6 real children (`ANDROID-CONTROL`, `DSI`, `EDITOR-URDF`, `IOS-CONTROL`) rendered as orphaned top-level rows instead of nested under their real parent, while only `STUDIO`/`SUITE` (whose names sort after `SERVER`) nested correctly. The already-correct online `_refresh()` worker sorts `combined` by `(family, parent-first, name)` before rendering; that same sort just wasn't applied to the offline/local-only path. Fixed by sorting inside `_render_rows()` itself (not just at one call site), so it's correct for every caller - offline refresh, a filter change, a language switch - regardless of `self.locals_`'s own order.
- **Real bug fixed in `tests/test_registry.py`**: a manifest fixture built inside a non-raw Python triple-quoted string double-escaped its embedded regex (`\\d+`, `\\.`), producing invalid JSON (`\d` is not a valid JSON escape) at runtime and making the test fail with `ManifestValidationError` instead of exercising what it was meant to test. Fixed by making the string literal raw (`r'''...'''`) so only JSON's own escaping applies.
- Verified real: `pytest tests/ -q` -> 17/17 (previously 16 passed, 1 failed). A real local-discovery harness against the actual `C:\Users\juane\Documents\GitHub` checkout confirmed the fix - `HYDRA-UMC-SERVER` now shows 6 real children (was 2), top-level rows dropped from 28 (broken) to the expected 16, all 47 real local manifests still accounted for, and Treeview selection still survives a real language switch.

## [0.2.6]

- **Fixed a second real ecosystem-discovery bug, found while verifying the
  0.2.5 fix above**: `service.port` was required whenever a `service`
  object was present at all, so a repo declaring only `systemd_unit` (a
  background systemd worker with no listening network port - e.g.
  HYDRA-UMC-COGNITIVE-NODE, HYDRA-UMC-VISION-NODE) still failed manifest
  validation with `service.port must be an integer between 1 and 65535`.
  `port` and `systemd_unit` are now each independently optional (at least
  one is still required), and `health_path` now gives a clear
  `service.health_path requires service.port` error instead of silently
  reading a `None` port. Verified against the live ecosystem: discovery
  went from 36/55 -> 42/55 after the 0.2.5 fix alone, and all remaining
  failures were this exact port-required bug.

## [0.2.5]

- **Fixed a real ecosystem-discovery bug**: `project_manifest.py`'s `service`
  object schema rejected the `systemd_unit` field (e.g.
  `"hydra-umc-server.service"`) that 19 repositories' own manifests already
  declared - `parse_manifest()` raised `ManifestValidationError: unknown
  field(s) in service: systemd_unit` for every one of them, so
  `discover_remote_projects()` silently dropped those 19 repositories from
  every consumer (the ecosystem dashboard showed 36/55 projects, not a
  crash - just a quietly incomplete list). `service.systemd_unit` is now a
  recognized optional field (`ProjectManifest.service_systemd_unit` /
  `ProjectEntry.service_systemd_unit`), validated as a string ending in
  `.service`, with real test coverage for the accepted, optional, and
  rejected-without-suffix cases.

## [0.2.4]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.3]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.2.2] - Real anti-rollback and manifest validation before an update

- **`install.py`'s `clone_or_pull()`** no longer trusts "Git can fast-forward
  it" as the definition of a safe update. Before touching the working tree it
  now: fetches the remote candidate without modifying the checkout, reads and
  validates both the installed and candidate revision's own repository-owned
  `hydra-umc.project.json` (`git show <rev>:hydra-umc.project.json`, no
  checkout mutation), and refuses the update outright if the candidate's own
  declared version is lower than what's installed - a real anti-rollback
  check, not just a fast-forward check. A cloned checkout that fails manifest
  validation is discarded the same way a failed clone already was.
- New `test_refuses_a_remote_manifest_version_lower_than_the_installed_version`
  proves a real, otherwise fast-forwardable downgrade is rejected and `HEAD`
  stays exactly where it was - the same "never silently replace a healthy
  checkout" guarantee `test_diverged_pull_fails_without_resetting_local_checkout`
  already proved for a diverged branch, now covering a second real failure
  mode.
- Fixed a real, self-inflicted accuracy bug found while reviewing this work:
  `clone_or_pull()` now runs `git fetch` + `git merge --ff-only FETCH_HEAD`
  instead of a plain `git pull --ff-only`, but its own docstring and error
  message still named the old command - both corrected to match what
  actually runs, and the one test asserting on that exact error string
  updated with them.
- `docs/CLI_REFERENCE.md` updated to describe the real manifest-based
  preflight and the new downgrade-rejection test.
- 37/37 tests passing (was 36).

## [0.2.1] - Fixed a real version-mirror drift

- **`src/hydra_umc_updater/__init__.py`**'s `__version__` had fallen one
  real build behind `pyproject.toml`/the manifest, found live: running
  `python main.py` after an earlier real version bump still showed the
  OLD version in the GUI's own title bar and About dialog. Root cause:
  `bump_manifest_version.py` (called bare, no `--sync`) only touches its
  declared `native_version.file` (`pyproject.toml`) - it doesn't know
  this repo also mirrors that version into `__init__.py`, which only
  this repo's own separate `bump_version.py` keeps in sync (called
  first, from `build.bat`/`.sh`). Fixed via the real, intended sequence
  this time (`bump_version.py` then `bump_manifest_version.py --sync`).
  The same underlying gap was found and fixed across every other
  ecosystem repo with this same pyproject.toml/__init__.py mirror
  pattern this same pass.

## [0.2.0] - Real Help > About window

- **A real native menu bar** (`gui.py`) - `Help > About` opens a real,
  read-only dialog: app name, real running version (`__version__`),
  copyright/license, a genuine clickable GitHub repository link (opened
  via the stdlib `webbrowser` module, no new dependency), and the real
  Python/Tk runtime this process is actually executing under - useful,
  honest diagnostic info for a desktop tool that runs across very
  different machines (a developer's own PC today, a CM5's own desktop
  session later). Fully translated in all 7 existing languages, relabeled
  live on a language switch like every other real widget in this window.
- Real bug found and fixed by actually running this on Windows: a
  top-level `tk.Menu` assigned as a window's own `-menu` silently gains
  an implicit tearoff entry at index 0 unless it *also* gets
  `tearoff=False` (not just its submenus) - without it,
  `menubar.entryconfig(0, ...)` targeted that phantom entry instead of
  the real "Help" cascade and failed with a real `TclError`. Verified via
  a real headless-but-live `Tk()` smoke test: the About dialog opens, and
  all 7 languages relabel the menu without error.
- 36/36 tests still passing.

## [0.1.9] - Real, optional service-liveness manifest field

- **`hydra-umc.project.json`'s own schema gains a real, optional `service`
  object** (`project_manifest.py`) - `{ "port": 1-65535, "health_path"?:
  "/some/path" }`. Absent for the common case (a library/CLI/firmware/UI
  that never runs as a network service); present only for a repo that
  actually does, so HYDRA-UMC-SERVER's ecosystem status endpoint (and any
  future dashboard) can do a real liveness probe against each declared
  sibling service instead of only reading static manifest metadata. Kept
  as a genuinely optional, explicitly-recognized field (not "anything
  goes") - an unrecognized key still fails loudly, same reasoning as the
  existing top-level unknown-field check. `registry.py`'s `ProjectEntry`/
  `entry_from_manifest()` carry the new `service_port`/
  `service_health_path` through to every existing consumer (local
  discovery, GitHub-based catalog) unchanged otherwise.
- 6 new tests in `tests/test_project_manifest.py` covering: absent by
  default, a real port+health_path pair, port-only (TCP-level check),
  an out-of-range port rejected, a health_path missing its leading `/`
  rejected, and an unknown key inside `service` rejected. Full suite:
  36/36 passing (was 30). Verified the change doesn't break real local
  discovery against the actual ecosystem checkout on this machine
  (`discover_workspace()` still lists every project cleanly).

## [0.1.8] - Real retries for transient network errors, real malformed-catalog fixtures

- **Real bounded retry with backoff for transient network failures** (`github_client.py`'s `_urlopen_with_retries`): every real GitHub request this tool makes (repository listing, manifest fetch, native-version fallback) used to treat the very first network hiccup (a dropped connection, a DNS blip, a timeout) as a permanent failure. It now retries up to 3 times with exponential backoff (0.5s, 1s) before giving up - but only for genuine transport-level failures (`URLError`/`TimeoutError`/`socket.timeout`/`OSError`), never for a definitive HTTP response GitHub already gave (a 404/403/500 is real information, not noise to retry through).
- **Real fixture-server tests for a malformed remote catalog** (`tests/test_github_client.py`, new): a real local `http.server.HTTPServer` now stands in for GitHub in tests - a malformed top-level repository-list JSON, an unexpected (non-list) response shape, and one malformed manifest mixed into an otherwise-valid catalog are each proven to fail the way the code already claimed to: a total catalog failure raises a clear `RuntimeError` (already caught gracefully by both `gui.py` and `main.py`, which fall back to a locally-discovered project list), while one bad manifest is isolated into `RemoteDiscovery.errors` without aborting discovery of the other, valid projects.
- 12 new tests (`tests/test_github_client.py`) = 30 total, including direct unit coverage of the retry/backoff logic itself (recovers after N transient failures, gives up after the real max, never retries a definitive `HTTPError`) and one real end-to-end proof against a genuinely unreachable host (`127.0.0.1:1`) that `_fetch_one` really does retry before reporting a network error.
- **A healthy local checkout is never silently replaced** - already true and already covered by `test_diverged_pull_fails_without_resetting_local_checkout` in `tests/test_install.py` (a real diverged git history, `pull --ff-only` fails loudly, HEAD and file content are proven unchanged). Re-verified as part of this pass; no code change was needed here.

## [0.1.7]

- **Real bug found and fixed via live testing**: the deploy filter's "All N projects" combobox entry showed "All 0 projects" from app startup until the user happened to switch languages. `_deploy_label("all")` embeds `len(self.locals_)`, but that count was only ever recomputed inside `_apply_language()` - called once at `__init__` time (before `self.locals_` had any real projects loaded into it) and again only on a manual language switch. Neither `_refresh()`'s offline pass nor the online GitHub-check worker (both of which really do update `self.locals_`) ever triggered a recount, so the combobox stayed stuck at the stale value from whichever `_apply_language()` call last ran. Fixed by extracting the label/value rebuild into `_refresh_deploy_filter()` and calling it from both real places `self.locals_` changes, not just from a language switch. Verified live: a real `UpdaterGUI` instantiated against the actual `C:\Users\juane\Documents\GitHub` checkout now shows "All 47 projects" immediately after construction (previously "All 0 projects"), and switching languages still updates the label correctly with no regression.

## [0.1.6]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.1.5]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.

## [0.1.1] - Real 7-language GUI translation

- **`i18n.py`** (new) - real, complete translations (not machine-placeholder text) for the windowed GUI's own UI chrome and closed vocabulary (maturity/role/deploy labels, install-state labels), in the same 7 languages (en/es/fr/it/de/zh/ja) this ecosystem's own READMEs and the public dashboard already ship. Deliberately does NOT translate project names, family names, or `notes`/`tech` free text - that stays `registry.py`'s own single source of truth, same reasoning as the dashboard's own `TRANSLATIONS` module. `--cli` mode stays English-only on purpose (meant to be scripted/piped).
- **Real language detection**: a previously saved choice (`~/.hydra_umc_updater_lang.json`) wins, then the OS's own configured locale (`locale.getlocale()`), then English - verified for real on this machine (a real Spanish-locale Windows install correctly auto-selected `es` with nothing configured).
- **`gui.py`** - every real widget (labels, buttons, checkboxes, column headings, status/state text, message boxes) now re-labels live via a new language `Combobox` next to the deploy filter, not just at startup; the current selection persists across a switch.
- **Real bug found and fixed via this pass's own live GUI testing**: `_render_rows()`'s full `delete()` + reinsert of the Treeview silently dropped the current row selection on ANY re-render (a language switch, a plain refresh, GitHub results arriving) - the notes panel would revert to its "nothing selected" placeholder even though the same real project was still logically selected. Fixed by remembering the selected iid(s) before the rebuild and restoring them afterward (for every real `_render_rows()` caller, not just the one that first surfaced it during testing).
- **13 new tests** (`tests/test_i18n.py`) - key-parity across all 7 languages, real template substitution, real fallback behavior (unknown language/key/placeholder), and real save/load round-trips against an isolated temp config file (`monkeypatch`, not the user's own real `~/.hydra_umc_updater_lang.json`).
- **`build.sh`/`build.bat`** - `i18n.py` added to the compile-check step.

## [0.0.9] - v3: real maturity/role/family classification for all 44 projects

- **`registry.py`** - `ProjectEntry` gains 5 new fields: `tech` (the real, specific technologies a project is built on, richer than the existing `stack` icon/filter category), `notes` (an honest sentence or two on what's actually implemented vs. still aspirational, separate from `note`'s build instructions), `maturity` (`"scaffolding"` / `"functional"` / `"established"` / `"production"` - see the module's own docstring for exactly how each of the 44 projects was assigned one, read from each project's own `CHANGELOG.md`, not guessed from its name or README), `role` (`"api"` / `"ui"` / `"cli"` / `"firmware"` / `"library"` / `"service"` / `"tool"`), and `family`/`parent` (the same family grouping the JuanenRac README's own "Project Catalog" tables already use, now with an explicit machine-readable parent - e.g. all 6 Data & Analytics children point `parent="HYDRA-UMC-DATALAKE"`).
- New derived indexes: `BY_MATURITY`, `BY_ROLE`, `BY_FAMILY`, `FAMILY_PARENT` (a family's own single parent, or `None` for a family with no single shared parent - "Complementary Tools" today), `CHILDREN_OF` (the real inverse of `ProjectEntry.parent`).
- **`gui.py`** - the Treeview is now a REAL parent/child tree (Tkinter's own native nesting, not a flat list): each family's parent is a top-level row with its real children nested directly under it, matching this registry's own family/parent fields. New Maturity/Role columns, maturity-based row coloring, and the notes panel now shows `entry.notes`/`entry.tech` alongside the existing build `entry.note`.
- **`main.py`** - `status` gained new MATURITY/ROLE columns and a `--notes` flag that prints each project's real notes/tech below the table.
- **`tests/test_registry.py`** - 19 new real tests (parametrized per family) verifying the new derived indexes' own internal consistency: every `parent` reference resolves, no project is its own parent, every family has exactly zero or one real parent (never a silently-picked default), `CHILDREN_OF` is a real inverse of `parent`, and registry declaration order always puts a family's parent before its children (both `detect.py`'s `scan_workspace` and the GUI's own tree-builder depend on that order).
- **`build.sh`/`build.bat`** - now install with dev extras and run the real test suite as a required step before the import check passes; `build.sh`/`build.bat`/`run.sh`/`run.bat` no longer auto-close their window on completion.
- This same pass regenerated `JuanenRac/docs/index.html` (the public dashboard) against this registry - see that repo's own CHANGELOG for the dashboard-side v3 changes (maturity/role badges, family/parent grouping, per-project notes).

## [0.0.4]
### Added
- Windowed GUI (`gui.py`, Tkinter/ttk, stdlib only) - now the DEFAULT way
  to run this tool (bare `hydra-umc-updater` / double-click), on both
  Windows (a developer's own PC) and Linux (the real CM5's own local
  desktop/VNC session). One window: a filterable project table (Project /
  Stack / Deploy target / Local / GitHub / State), a deploy-target
  dropdown, Refresh, and Install/Update buttons for the selected project -
  calling straight into the same `detect.py`/`github_client.py`/
  `install.py` the CLI already used, so there is exactly one
  install/update implementation, not two that could drift apart.
- `--cli` flag switches to the previous headless argparse CLI
  (`status`/`install`/`update`) - follows the exact
  `if "--cli" not in sys.argv: import tkinter` pattern already established
  by `URTC-FLASHER/urtc_flasher.py`, so `--cli` mode never needs tkinter
  installed or a display present, and a genuinely headless CM5 (no
  `python3-tk`) still works via `hydra-umc-updater --cli status`.
- `registry.py`: new `ProjectEntry.deploy` field ("cm5" / "user-pc" /
  "mobile" / "wearable") - not every one of the 44 projects actually
  belongs on the compute module itself. Reclassified all 44: 31 are real
  CM5-hosted services (SERVER/STUDIO/DSI/DASHBOARD-AI plus the Vision,
  Cognitive, Orchestration, Digital-Twin, Data, and Industrial-Gateway
  families), 10 are user's-own-PC tools that never get checked out or run
  ON the CM5 (every URTC-prefixed repo including URTC's own firmware -
  compiled/flashed from a PC, the CM5 only ever needs the resulting .bin
  over CAN-OTA, not this repo's own source - plus HYDRA-UMC's own
  firmware, HYDRA-UMC-SUITE, HYDRA-UMC-EDITOR-URDF, and
  HYDRA-UMC-TOOL-CLI), 2 are mobile apps, and 1 is the wearable. The GUI's
  table defaults to filtering to "CM5" on Linux and shows everything on
  Windows/macOS - always overridable from the dropdown.

### Verified
- Real GUI smoke test against the actual 44-project checkout: window
  construction, the offline local scan populating all 44 rows, and the
  deploy-target filter narrowing to the expected 31 (CM5) / 10 (user-pc)
  rows. `--cli status --offline` re-verified unaffected (still 44/44
  installed, 0 parse failures) after the dispatch change in `main.py`.

## [0.0.2]
### Added
- Initial working implementation - `registry.py` (all 44 ecosystem
  projects: repo, stack, version file, extraction pattern), a shared
  `version_parse.py` used identically for local and GitHub-fetched text,
  `detect.py` (local workspace scan), `github_client.py` (concurrent raw
  GitHub content fetch of every project's latest version), `install.py`
  (git clone/pull + delegate to the target project's own build script),
  and `main.py` (the `status`/`install`/`update` CLI).
- Copyright/license header on every source file and build/run script.
- `CHANGELOG.md` (this file), full community-health files, and README.md
  plus its 4 translations.

### Verified
- Real end-to-end run against the actual 44-project ecosystem checkout:
  local detection correctly read all 44 real version files with zero
  parse failures, and the real GitHub check (raw.githubusercontent.com,
  no API token needed for public repos) correctly reported 41/44 as
  "up to date" and 3 as "ahead of GitHub" - exactly the 3 projects with
  local, not-yet-pushed changes at verification time. Not a synthetic
  test - the actual registry data, the actual local files, the actual
  public GitHub repos.
