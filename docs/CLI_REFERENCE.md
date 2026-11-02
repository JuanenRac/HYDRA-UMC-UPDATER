# HYDRA-UMC-UPDATER — CLI Reference

`hydra-umc-updater` defaults to a windowed Qt Quick GUI. Passing `--cli` switches
to the headless argparse CLI documented here, before the optional desktop
runtime is imported, so `--cli` mode works on a genuinely headless CM5 with
no Qt/PySide6 desktop runtime installed and no display. Every example below was captured from a real
run of the installed CLI — not written from memory.

## Usage

```
$ hydra-umc-updater --cli -h
usage: hydra-umc-updater --cli [-h] [--version]
                               {status,install,update,train,deploy-plan,evidence,prune-backups} ...

Detects, installs, and manually updates the HYDRA-UMC ecosystem's own projects
on this machine.

positional arguments:
  {status,install,update,train,deploy-plan,evidence,prune-backups}
    status              Show what's installed, its version, and the latest
                        GitHub version of every project.
    install             Clone and build ONE project that isn't installed yet.
    update              Pull and rebuild ONE project that's already installed.
    train               Install a tested set of versions (a train) instead of
                        the head of every project; dry run by default.
    deploy-plan         Show what the device would need to run what the
                        workspace has (read-only; --apply --yes deploys,
                        behind the os_deploy switch).
    evidence            Export the evidence of the update attempts to an
                        outbox file (and the data lake), or verify it.
    prune-backups       Remove old '<project>.backup-xxxxxxxx' folders,
                        keeping the newest few of each project.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

```
$ hydra-umc-updater --cli --version
hydra-umc-updater <installed version>
```

`install`/`update` are deliberately separate from `status` and always
take one explicit project name — there is no "update everything". A
fleet of real robots is not something to leave auto-updating
unattended: `status` shows what's outdated, a human picks what to
actually touch.

## Commands

### `status [--workspace PATH] [--offline] [--notes] [--json]`

```
$ hydra-umc-updater --cli status -h
usage: hydra-umc-updater --cli status [-h] [--workspace WORKSPACE] [--offline]
                                      [--notes] [--json]

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace root to scan (default: this tool's own
                        parent directory).
  --offline             Skip the GitHub check - local state only.
  --notes               Also print each project's real notes (family/parent,
                        what's actually implemented, tech) below the table.
  --json                Machine-readable JSON instead of the human-readable
                        table (ignores --notes).
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

Fetches the remote candidate, validates its repository-owned
`hydra-umc.project.json` before modifying the checkout, rejects a candidate
whose semantic version is lower than the installed manifest, then performs a
`git merge --ff-only` in an independent staging clone, runs the project's own
`build-test` script there unless `--no-build` is given, and only then swaps the
verified clone into place (the previous installation stays beside it as
`<name>.backup-xxxxxxxx`). The preflight is deliberately manifest-based: a reachable Git commit is
not automatically a safe ecosystem update. `--ff-only` is
deliberate and load-bearing: **a healthy local checkout is never
replaced**. A real local edit (this tool is meant to also run on a
developer machine, not only the CM5) or a diverged branch makes the
update fail loudly — and when the cause is a commit that exists only in
the local checkout, the message names it — never a silent reset or a
discarded change:

```
$ cd /path/to/workspace/SOME-PROJECT && git log --oneline -1
a1b2c3d local work in progress
$ hydra-umc-updater --cli update SOME-PROJECT
FAIL git merge --ff-only failed: .../SOME-PROJECT has 1 local commit(s) that the upstream does not have (a1b2c3d local work in progress), so the update cannot be a fast-forward - ...
$ cd /path/to/workspace/SOME-PROJECT && git log --oneline -1
a1b2c3d local work in progress   # unchanged
```

(Exercised for real in `tests/test_install.py`'s
`test_diverged_pull_fails_without_resetting_local_checkout`: a real
diverged git history is built, the fast-forward is proven to fail, and
`HEAD`/file content are proven byte-for-byte unchanged afterward. The separate
`test_refuses_a_remote_manifest_version_lower_than_the_installed_version`
proves that an otherwise fast-forwardable downgrade leaves `HEAD` unchanged.)

### `deploy-plan [--workspace PATH] [--install-plan FILE] [--device-root DIR] [--json] [--apply --yes]`

What would have to be deployed on the device so that it runs what the workspace has. It crosses the table of
installers of HYDRA-UMC-OS (`HYDRA-UMC-OS/provisioning/install_plan.json` of the workspace, or `--install-plan`),
the manifest of every checkout and the manifest each installer leaves next to the installed program
(`/opt/hydra-umc/<component>`, or below `--device-root` / `HYDRA_UMC_UPDATER_DEVICE_ROOT` / the `device_root`
setting when the tree is somewhere else). Each project is reported as `deploy` (the device runs an older
version: a step), `current`, `ahead` (the device is newer than the checkout), `not-installed` (a first
installation is done by hand with its installer, never by the plan), `not-cm5`, `manual` (its installer does not
follow the deployment contract), `no-checkout` or `unknown`; the steps come in `depends_on` order. Without
`--apply` it only reads files: nothing is installed or run. `--json` prints `schema_version`, `steps` and one
object per project (`project`, `state`, `checkoutVersion`, `deviceVersion`, `unit`, `target`, `command`, `note`).

`--apply --yes` deploys the steps through `hydra-umc-os deploy <PROJECT> --apply` (the same deployment as the
`os_deploy` switch, with its health check and its way back). It does nothing without `--yes`, nothing while the
`os_deploy` switch is off, checks the signature of each checkout first when signatures are required, stops at the
first step that does not hold and leaves one line of evidence per step. Exit code `0` when the plan was read (or
every step deployed), `1` when the table cannot be read or a step failed.

### `image verify RELEASE_JSON IMAGE [--trusted-keys FILE] [--require-tag] [--repo DIR] [--lang CODE] [--json]` - check a signed image release

The updater does not download or install operating-system images; this command is the contract for whoever hands it one.
It checks a release made by the image builder (`release-manifest` + `release-sign`): `release.json` (format
`hydra-image-release/1`), `release.json.sig` next to it, and the image. It only reads: nothing is written, applied or
installed. Exit code `0` when the release holds; `1` with the reason on stderr (in the language of the window, or `--lang`)
and the line "nothing was applied" when it does not.

Checks, in this order, and any failure refuses the release:

1. the file of trusted keys loads and holds at least one unrevoked key (no file, an unreadable or malformed one: refused);
2. `release.json` is valid JSON of format `hydra-image-release/1`;
3. `release.json.sig` is an Ed25519 signature, by one of the trusted keys, of the domain tag
   `hydra-umc-os-rebuilder-release/1` plus the SHA-256 of the exact bytes of `release.json` (a signature made for another
   purpose, such as a signed profile, does not verify; a key marked `revoke` is refused as revoked);
4. only then are the fields trusted: `image` (a plain file name), `size`, `sha256`, `version`, `commit` (40 hexadecimal
   characters) and `tag` must be well formed, and the image given must have that name, size and SHA-256;
5. with `--require-tag` (or `image_release_require_tag`): `git verify-tag TAG` succeeds in `--repo` and the tag points at
   exactly the `commit` of the release.

The trusted keys are PUBLIC keys in a file you control: one per line, 64 hexadecimal characters (a raw 32-byte Ed25519 key),
an optional label, `#` for comments, and `revoke KEY` to withdraw one. Several keys may be trusted together, so a key is
rotated by adding the new one, publishing with it and then revoking the old one. The fingerprint of the key that signed the
release is printed (compare it with the one the maintainer publishes). No private key is ever read, and nothing is printed
that could be one.

| Setting | Environment | Meaning |
|---|---|---|
| `image_release_trusted_keys` | `HYDRA_UMC_UPDATER_IMAGE_TRUSTED_KEYS` | The file of trusted public keys. Without it the command refuses everything. |
| `image_release_require_tag` | `HYDRA_UMC_UPDATER_IMAGE_REQUIRE_TAG` | `true`/`false`; off by default. The signature of the manifest is always required, whatever this says. |
| `image_release_repo` | `HYDRA_UMC_UPDATER_IMAGE_RELEASE_REPO` | The local clone in which the tag is checked. |

Needs the optional `cryptography` package (`pip install "hydra-umc-updater[signing]"`); without it the release is refused.
Tested with releases built in the tests with ephemeral keys in the format of the image builder; never run against a real
image, a real release or the device.

### `evidence export|verify` - hand the evidence of the attempts to the fleet

`evidence.jsonl` (in `.hydra-umc-updater` of the workspace) holds one line per install or update attempt.
`evidence export` turns the new lines into envelopes chained by sha256 (each carries its own hash and the hash
of the one before) and appends them to `evidence-outbox.jsonl`; `--push` also sends the envelopes the data lake
has not accepted to `POST /ingest/batch` as samples of kind `updater_attempt` (source `<node>/<project>`,
fields `ok` and `seq`). `evidence verify [--file FILE]` checks that an outbox, or a copy of it, is an unbroken
chain: a changed, removed or reordered envelope is found. Exporting is **off** unless
`HYDRA_UMC_UPDATER_EVIDENCE_EXPORT=1` or `evidence_export: true` is set; verifying only reads.

Settings (all in the settings file; none is a secret): `evidence_export_url` (base address of the data lake),
`evidence_export_token_file` (a file with the ingest token, or `HYDRA_UMC_UPDATER_DATALAKE_TOKEN_FILE`; the token
is never printed or stored in the settings), `evidence_export_allow_plain_http` (off: plain HTTP is only accepted
for this machine), `node_name` (default: the host name, or `HYDRA_UMC_UPDATER_NODE_NAME`). A redirect is never
followed, so the token only goes to the address that was checked. The outbox is the source of truth: a crash
never repeats or skips a line, a refused push is retried from the same envelope, and an evidence file shorter
than the outbox stops the export until someone looks at it. A line written before the evidence file kept a time
takes the time of the export and is marked `atEstimated`. Taking the outbox into the ops agent is done on its side.

### `prune-backups [--workspace PATH] [--keep N] [--dry-run]`

Every promoted update leaves the previous installation beside the new one as
`<name>.backup-xxxxxxxx`, and nothing removes those on its own. This command
keeps the newest `--keep` backups of each project (default 2) and removes the
rest; `--dry-run` only lists what it would remove. It never runs unless asked,
and refuses to start while an install or update is running in the workspace.

### `train plan|apply|rollback|make|trash` - install a tested set of versions

By default every project is installed or updated to the head of its repository
or its latest release, one at a time. A **version train** is a tested set of
versions, described by one file, that is installed together. It is off unless
the switch is on: `HYDRA_UMC_UPDATER_TRAINS=1` (or `"version_trains": true` in
the saved settings; a damaged settings file counts as off). With the switch off
`install`, `update` and the window behave exactly as before.

```
train plan     FILE [--workspace PATH] [--offline] [--allow-downgrade] [--json]
train apply    FILE [--workspace PATH] [--offline] [--allow-downgrade] [--json] [--yes] [--no-build]
train rollback      [--workspace PATH] [--offline] [--json] [--yes] [--no-build] [--remove-new]
train trash    [--list] [--json] [--empty --yes --i-understand] [--workspace PATH]
train make     --out FILE [--name NAME] [--from-release FILE] [--force] [--require-manifests] [--no-manifest-fill] [--workspace PATH]
train sign     FILE --key-file PATH
train keygen   [--out-dir PATH] [--name NAME]
```

- `plan` only reads. It explains, per repository and in `depends_on` order, what
  would be installed and why (`INSTALL`, `UPDATE`, `DOWNGRADE`, `KEEP`,
  `BLOCKED`) and exits `1` when the train has problems. For a repository that is
  already installed and differs it fetches the Git objects (never the files) to
  check the pinned commit; `--offline` skips the fetch, and a pinned commit that
  is not already in the checkout is then a problem.
- `apply` is a **dry run** (the plan is printed, nothing is installed) unless
  `--yes` is given, and `--yes` also needs the switch on. It installs only what
  differs, in dependency order, through the same safe flow as `update` (isolated
  staging clone, build, signature check when required, promotion with a backup)
  but on the commit of the train instead of the head. It stops at the first
  failure; the repositories before it stay installed.
- `rollback` puts back the state saved before the last `apply` (`.hydra-umc-trains/previous.json`
  in the workspace; the file is renamed, never deleted, once used). It is also a
  dry run without `--yes`. A repository that the train installed for the first
  time is left installed unless `--remove-new` is given. The saved state is written by
  the updater itself, so it is not checked against a signature.
- `rollback --remove-new` (with `--yes` and the switch on) also takes away the repositories the
  last `apply` cloned for the first time (`.hydra-umc-trains/first-installed.json`, written one by one
  as each clone succeeds). Nothing is deleted: each folder is moved to `.hydra-umc-trains/trash/NAME.removed-XXXXXXXX`
  inside the workspace (move it back to restore it). A repository is moved only if it is a plain Git checkout directly
  inside the workspace (no link pointing elsewhere), is still on the exact commit the train installed
  and has no modified, staged or untracked files, and no other installed repository (one that is not being
  removed too) lists it in the `depends_on` of its manifest. If any one of them fails a check the whole rollback stops with
  `BLOCKED` and exit `1` before anything is restored or moved, and the check is made again right before moving.
  A damaged record stops `--remove-new`; a plain rollback only warns. Repositories that were installed before the
  train are never removed, only put back. The record is renamed (not deleted) once the removal is done.
- `trash` shows what the rollbacks moved aside (`--list`, the default; `--json` for a reader). The trash is never
  emptied by itself. `trash --empty` deletes its content **for good and cannot be undone**, so it needs both
  `--yes` and `--i-understand`; with fewer it deletes nothing and exits `1`. It only touches the children of
  `.hydra-umc-trains/trash` in the workspace (a link inside is removed as a link, never followed; a trash that is
  itself a link, or not a real folder there, is left alone), and the repositories of the workspace are not reachable
  from it. The folder is kept.
- `make` writes a train for the projects checked out in the workspace: `--out FILE`. Which repository, version
  and commit are listed comes from the release generator of the family (`tools/ecosystem_release.py` of
  `HYDRA-UMC-SDK`, run with `--print`; its logic is not repeated here), or from a published
  `ecosystem-release.json` with `--from-release`. The `digest` is added and the result is parsed again, so the updater
  accepts what it writes; a missing or failing generator writes nothing, and an existing file is not replaced without
  `--force`. For every repository that is checked out in the workspace it also fills in `manifest_sha256` (the sha256 of
  `hydra-umc.project.json` at the listed commit) and `depends_on` (the list that manifest declares, `[]` when it declares
  none), after the same verification `plan` makes: the commit exists and belongs to the history of the checkout, the
  manifest there is valid and names the listed version. The finished train must also be consistent (every dependency is
  in the train or installed, no cycle). Any failing check writes nothing and exits `1`. A repository that is not checked
  out cannot be verified: it is left without the two fields and named in a `NOTE:` on the error output, or refused with
  `--require-manifests`; `--no-manifest-fill` skips the reading of the manifests altogether. It does not sign: when a signature is required it prints the next step, `train sign FILE --key-file PATH`.
- `sign` writes `FILE.sig`, an Ed25519 signature of the exact bytes of the train, with a private key read
  from a file (`--key-file`, or `HYDRA_UMC_UPDATER_TRAIN_KEY_FILE`). It refuses a train the updater would
  not read, a key file that is not 64 hexadecimal characters and, on Linux, a key file readable by anyone
  but its owner. The key is never printed, put on a command line or stored by the updater.
- `keygen` makes a new Ed25519 pair: `NAME.key` (private, 64 hexadecimal characters, owner only) and `NAME.pub`
  (public) in `~/.hydra-umc-keys` (or `--out-dir`). It never overwrites a file and prints only the paths and the
  public key, which is then pinned with `HYDRA_UMC_UPDATER_TRAIN_PUBKEY` or the `train_public_key` setting.
  The private key must stay out of every repository.

**The train file** has the shape of the family's `ecosystem-release.json`
(`schema_version` `"1.0"`, `ecosystem` `"HYDRA-UMC"`, `repositories` with `name`,
`version` and the full 40-character `commit`) plus optional fields. Any other key
is refused, and a malformed train installs nothing:

| Field | Meaning |
|---|---|
| `name` (top level) | Label shown in the plan. |
| `digest` (top level) | sha256 of the canonical `repositories` list; a file whose content no longer matches is refused. |
| `manifest_sha256` | sha256 of `hydra-umc.project.json` at that commit; a mismatch refuses the repository. `train make` fills it in. |
| `depends_on` | Must equal the manifest's `depends_on` at that commit. `train make` fills it in. |
| `requires_min` | Minimum versions of other repositories (for example the SDK) that the train, or what is installed, must satisfy. |

**What is checked before anything is installed:** the file is well formed and its
digest matches; every `requires_min` is met by the train (or by what is
installed); every `depends_on` is in the train or installed and the graph has no
cycle; for each installed repository that differs, the commit exists, is part of
the published history (an ancestor of the remote head), its manifest validates,
names the listed version and has the listed digest, and the checkout has no
uncommitted changes; an installed version newer than the train needs
`--allow-downgrade` (the anti-rollback rule of `update` is kept). A repository that
is not installed yet is checked right after the clone and, if any check fails,
nothing is installed for it. Commit signatures are checked as for `update` when
they are required.

**Signed trains.** The digest only catches an accidental change: whoever can edit the file can recompute
it. With `require_signed_trains` on, `train plan` and `train apply` accept a train only
when `FILE.sig` holds a valid Ed25519 signature of the exact bytes of the file made by the public key pinned
in the configuration. The file is read once, checked and then parsed, so what was verified is what is
installed. A missing, malformed or wrong signature, no pinned key, a key that is not an Ed25519 key and a
machine without the `cryptography` package (`pip install "hydra-umc-updater[signing]"`) all refuse the
train: nothing is installed and the message never contains key material.

| Setting | Environment | Meaning |
|---|---|---|
| `require_signed_trains` | `HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS` | `true`/`false`. When unset it follows `version_trains`: a signature is required whenever trains are on. A damaged settings file counts as required. |
| `train_public_key` | `HYDRA_UMC_UPDATER_TRAIN_PUBKEY` | The trusted public key: 64 hexadecimal characters (a raw 32-byte Ed25519 key) or the path of a file holding them. |

Turning the requirement off is a deliberate choice; keep the train file in a place only you can write.
Because the key is pinned in the configuration of each machine, a signature made with another key (or
a train signed after someone replaced the file) is refused. The signature covers the file, not the
contents of the repositories: those are still checked against the pinned commits.

Writing a train: `train make --out FILE` (see above). The optional fields (`manifest_sha256`, `depends_on`,
`requires_min`) are added by hand; `train_to_json` in `hydra_umc_updater.train` writes the file again with its `digest`.

**`train plan --json` (stable output).** A single JSON object; a reader (such as a read-only view) can rely on these keys:

| Key | Meaning |
|---|---|
| `schema_version` | `"1.0"`. Keys are only ever added in a minor change; a removed or renamed key raises the major number. |
| `train` | Name of the train. |
| `ok` | `true` when the train has no problems (exit code `0`). |
| `problems` | List of texts; empty when `ok`. |
| `items` | One object per repository in `depends_on` order: `name`, `action` (`install`, `update`, `downgrade`, `keep` or `blocked`), `version` and `commit` (the train's), `installed_version` and `installed_commit` (`null` when not installed), `reason`. |

`rollback --json` adds `removals` (objects with `name`, `action` = `remove`, `gone` or `blocked`, `commit`, `reason`)
and `remove_new`.

## Safety limits

- One install or update at a time per workspace (the lock file
  `.hydra_umc_updater.lock` in the workspace); a second one stops with
  "another install or update is already running".
- Every git command is stopped after 300 s and every `build-test` after
  1800 s, and none of them may stop to ask for credentials.
- `HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1`, or `require_signed_commits` in
  `~/.hydra_umc_updater_settings.json` (an unreadable settings file counts as
  on), requires the candidate commit to carry a signature `git verify-commit`
  accepts, for a first install as well as for an update. An ssh signature is
  checked against the file named by `allowed_signers_file` in the same
  settings, when it is set.
- A project that declares a service port and a health path is checked after its
  checkout is replaced, and the update counts as done only when the check
  answers with a 2xx. By default that is one attempt.
  `HYDRA_UMC_UPDATER_HEALTH_RETRIES=N` (at most 10) makes it up to N attempts,
  waiting `HYDRA_UMC_UPDATER_HEALTH_RETRY_DELAY` seconds (default 2, at most
  30) before the second one and twice as long before each next one, for a
  service that needs a few seconds to start. With
  `HYDRA_UMC_UPDATER_ROLLBACK_ON_UNHEALTHY=1` (off by default) a check that
  still fails after the last attempt puts the previous installation back and
  reports the update as failed; the promoted checkout stays next to it as
  `<name>.unhealthy-xxxxxxxx`. The updater itself never restarts a service.
- On the device, the program that runs is not the checkout: it is the one the
  installer of HYDRA-UMC-OS put in `/opt/hydra-umc`. With
  `HYDRA_UMC_UPDATER_OS_DEPLOY=1` (or the saved setting `os_deploy`; off by
  default, the environment wins) the updater runs `hydra-umc-os deploy
  <PROJECT> --apply` after a promotion (through `sudo -n` when it is not root;
  `HYDRA_UMC_UPDATER_OS_DEPLOY_COMMAND` names another command). The installer of
  the project keeps the program in use, installs the promoted one, restarts the
  unit if it runs, polls its health route and puts the old program back if it
  does not come back; the health check above then looks at the restarted
  service. A project without an installer that follows the deployment contract
  is a normal update; a deployment that did not hold (status 3), failed or could
  not start is a failed update, and with
  `HYDRA_UMC_UPDATER_ROLLBACK_ON_UNHEALTHY=1` the previous checkout is put back
  too. The command is `sudo`-run: the account of the updater needs a sudoers
  rule for it, which this project does not write.
- `HYDRA_UMC_WORKSPACE` names the workspace when `--workspace` is not given.
  When the updater is installed as a package inside a Python environment, the
  current directory is used instead of a folder inside that environment.

## Order of a batch and one run at a time

- A project whose `hydra-umc.project.json` lists other repositories in
  `depends_on` is installed or updated after the ones it names that are part of
  the same batch. The SDK still goes first and the updater last; a dependency
  outside the batch is ignored and a cycle cannot lose a project. The
  confirmation list shows the same order. The manifest parser accepts the field
  (unique repository names, never the project's own).
- A lock file in the workspace allows one install or update at a time: two
  windows, a window and the command line, or this tool and another one cannot
  run the promotion renames and write the journal together.
- The cache in the user's home directory (next to the settings file) is turned
  off with `HYDRA_UMC_UPDATER_NO_CACHE=1`.

## Exit codes

`status` always exits `0` (even when projects are outdated — that's
informational, not a failure). `install`/`update` exit `1` on any real
failure (unknown project, failed clone/pull, failed build script, a workspace
that is busy, an unexpected error) and `0` on success. `train` exits `1` for a malformed or inconsistent train, a switched-off `--yes`, a failed installation, and `0` otherwise (a dry run of a good train is `0`). `prune-backups` exits `0`
unless the workspace is busy or `--keep` is negative.

## Network resilience

Every real GitHub request `status` makes (repository listing, manifest
fetch) retries up to 3 times with backoff for a genuinely transient
network failure (DNS/timeout/connection reset) before giving up — never
for a definitive HTTP response GitHub already returned (404/403/500). If
the remote catalog itself is unreachable or malformed, `status` falls
back to local-only state with a `WARNING:` line instead of crashing.

## GUI

The preferred desktop client is the Qt Quick/QML interface. It is supplied by
the optional `PySide6` extra and uses the same discovery and update services as
this CLI; see [QML Desktop GUI](QML_DESKTOP_GUI.md). `--cli` remains fully
stdlib-only for a headless CM5. A Tkinter window can still appear only as a
temporary compatibility fallback when the optional Qt runtime is absent.

Running `hydra-umc-updater` with no arguments opens the QML desktop client.
On Windows, `run-gui.vbs` is the console-free double-click launcher; bare
`run.bat` delegates to it. The client provides a filterable project table,
explicit Install/Update actions, real in-window checkpoints and a language
selector (8 languages; the CLI itself stays English-only, since it's
meant to be scripted/piped).
