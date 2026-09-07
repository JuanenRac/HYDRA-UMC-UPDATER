# =============================================================================
# HYDRA-UMC-UPDATER - Clone/pull + delegate to each project's own build
# script: install.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Deliberately does NOT reimplement per-stack build logic (npm/cargo/go/
# gradlew/flutter/pip, 7 different toolchains across the ecosystem). Every
# project carries the common non-versioning build-test.sh/.bat entry point.
# It delegates to its own stack-aware check without incrementing a manifest or
# CHANGELOG, so fleet maintenance cannot manufacture a release merely by
# refreshing a checkout. Versioned build scripts remain an explicit human
# release action and are never selected here. The shared build-test entry point
# already knows its own real
# dependencies, venv/toolchain setup, and quirks (HYDRA-UMC-TELEMETRY-
# COLLECTOR/HYDRA-UMC-TOOL-CLI's module root being src/, not the repo
# root, for instance). Reimplementing that here would mean two places that
# both claim to know how to build a given project, guaranteed to drift.
# This module's own job ends at "clone/pull the source, then run whichever
# build script this specific checkout actually has."
# =============================================================================
from __future__ import annotations

import subprocess
import os
import time
from shutil import copy2, copytree, rmtree
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .project_manifest import ManifestValidationError, ProjectManifest, parse_manifest
from .registry import ProjectEntry, github_repo_url

# Checked in this order - the first one that exists in the checkout is the
# one actually run. Covers every real name used across the 44 projects
# (see this module's own header comment) without needing a per-project
# override in registry.py for something this mechanical.
BUILD_TEST_SCRIPT_POSIX = "build-test.sh"
BUILD_TEST_SCRIPT_WINDOWS = "build-test.bat"

# The GUI consumes these events to show the same real work that the CLI does.
# A callback is deliberately optional: command-line users retain normal child
# process output, while the GUI captures it so Windows never needs a second
# terminal window merely to show a project's build output.
ProgressCallback = Callable[[str, str], None]


@dataclass
class InstallResult:
    ok: bool
    message: str
    output: str = ""


def _run(
    cmd: list[str], cwd: Path, *, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {"cwd": str(cwd), "check": False}
    if capture_output:
        kwargs.update({"capture_output": True, "text": True})
    # The GUI is started with pythonw on Windows. Do not let git or a child
    # build script create a surprise console while its output is captured for
    # the in-window checkpoint log.
    if capture_output and os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        # Ecosystem .bat files deliberately finish with `pause` when an
        # operator double-clicks them.  In the GUI they run as a child with
        # captured evidence instead, so provide one harmless newline and do
        # not leave a hidden child waiting forever for a keypress.
        kwargs["input"] = "\n"
    return subprocess.run(cmd, **kwargs)  # type: ignore[arg-type]


def _rmtree_best_effort(path: Path) -> None:
    """Removes a staging directory this module created and no longer
    needs, tolerating a Windows-specific rough edge: a child process (git,
    or a project's own build-test.sh/.bat) can leave a file handle open
    for a brief moment even after that process has already exited,
    turning an immediate rmtree into a spurious PermissionError. Retries
    a few times with a short pause instead of either raising (this is
    always best-effort cleanup of OUR OWN temporary directory, never
    something that should fail the caller's own real result) or silently
    giving up on the very first attempt."""
    for attempt in range(5):
        try:
            rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == 4:
                return
            time.sleep(0.2)


def _checkpoint(progress: ProgressCallback | None, phase: str, message: str) -> None:
    if progress is not None:
        progress(phase, message)


# REV-002 (found in an independent revalidation audit, P1): well-known
# build-artifact directory names, never carried over by
# _carry_over_local_data() below even though git genuinely considers
# them untracked/ignored - always safe to regenerate, and carrying them
# over would risk a large, slow copy that also contaminates the staging
# clone's own freshly-verified build with stale artifacts. Same real
# convention this ecosystem's own generic tools/build_test.py already
# excludes when walking a checkout.
_NEVER_CARRIED_OVER_DIR_NAMES = {
    ".git", "node_modules", "dist", "build", "target", ".venv", "venv",
    "__pycache__", ".next", ".cache", ".pytest_cache", ".mypy_cache",
}


def _real_untracked_paths(path: Path) -> list[str]:
    """Returns every real path (relative to `path`) this checkout's own
    git considers untracked OR ignored (`git status`'s own `??`/`!!`
    codes) - the exact real local-data shape REV-002 needs carried over
    into a staging clone, which `git clone --local` never copies (it
    only ever copies the committed object database). Deliberately never
    includes a modified TRACKED file - a genuinely dirty working tree on
    a tracked file already fails clone_or_pull's own `git merge
    --ff-only` step separately, a different real problem this is not
    trying to solve."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "-z"],
        cwd=str(path), check=False, capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    paths: list[str] = []
    for entry in result.stdout.split("\0"):
        if len(entry) < 4:
            continue
        status_code, rel_path = entry[:2], entry[3:]
        if status_code in ("??", "!!"):
            paths.append(rel_path)
    return paths


def _tracked_dirty_paths(path: Path) -> list[str]:
    """Returns every real path (relative to `path`) this checkout's own
    git considers a TRACKED file with a real uncommitted change - staged
    or not (`git status --porcelain`'s own status codes other than
    `??`/`!!`, which _real_untracked_paths() already owns).

    V07-001 (found in an independent revalidation audit, P1): this
    module's own docstring used to claim "a real local edit... fails
    loudly with git's own error instead of being silently discarded" -
    true only for the older verify_build=False in-place `git merge
    --ff-only` path. Once UPD-01 moved the default (verify_build=True)
    flow to an isolated staging clone, that claim silently stopped being
    true: `git clone --local` only ever copies the COMMITTED object
    database, so a real uncommitted edit to an already-tracked file
    lives ONLY in `path`'s own working tree and is invisible to the
    fresh, clean staging clone - its own `git merge --ff-only` always
    succeeds (nothing there conflicts), the build succeeds, and
    promotion renames the dirty original aside to `.backup`, so the
    real edit survives only there while this function's own caller
    still reports `ok=True`. Checked explicitly, upfront, so this can
    fail loudly again before any staging work happens at all - matching
    what the docstring already promised."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=str(path), check=False, capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    paths: list[str] = []
    for entry_text in result.stdout.split("\0"):
        if len(entry_text) < 4:
            continue
        status_code, rel_path = entry_text[:2], entry_text[3:]
        if status_code in ("??", "!!"):
            continue  # real untracked/ignored data - _carry_over_local_data()'s own concern, not a rejection reason
        paths.append(rel_path)
    return paths


def _carry_over_local_data(old_path: Path, staging_path: Path, *, progress: ProgressCallback | None = None) -> None:
    """Copies every real untracked/ignored file or directory from
    `old_path` into `staging_path` before the candidate is built or
    promoted.

    REV-002 (found in an independent revalidation audit, P1): a real
    project's own operational data living inside its checkout (`data/
    settings.json`, `data/users.json`, a real sqlite file, TLS material a
    project generated for itself, ...) is exactly the shape of file `git
    clone --local` never copies at all - it only ever copies the
    committed object database. Reproduced with a real untracked file
    dropped into a real git checkout before an update: the promoted
    checkout was missing it entirely afterward, while the (kept, never
    deleted) `.backup` checkout still had it - a real, silent data loss
    on every update of a project that keeps any real local state inside
    its own checkout, which describes most services in this ecosystem
    (see this module's own header comment on why relocating that data
    outside every checkout entirely is real, separate, future work this
    fix does not attempt)."""
    carried = 0
    for rel_path in _real_untracked_paths(old_path):
        if rel_path.split("/")[0] in _NEVER_CARRIED_OVER_DIR_NAMES:
            continue
        source = old_path / rel_path
        if not source.exists():
            continue  # a real race (removed between `git status` and now) - nothing left to carry
        destination = staging_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            copytree(source, destination, dirs_exist_ok=True)
        else:
            copy2(source, destination)
        carried += 1
    if carried:
        _checkpoint(
            progress, "validation",
            f"Carried {carried} real local data file(s)/director(y/ies) from the installed checkout into the verified candidate.",
        )


def _validated_manifest_text(text: str, entry: ProjectEntry) -> ProjectManifest:
    """Parse the repository-owned manifest used as an update precondition.

    The updater never treats a Git revision as deployable merely because it
    can be fetched. It must still identify itself as the project selected by
    the operator and retain a valid public manifest.
    """
    return parse_manifest(text, expected_name=entry.name)


def _version_tuple(manifest: ProjectManifest) -> tuple[int, int, int]:
    return tuple(int(part) for part in manifest.version.split("."))  # type: ignore[return-value]


def _manifest_from_revision(path: Path, revision: str, entry: ProjectEntry) -> ProjectManifest:
    """Read a manifest from Git without modifying the working tree."""
    result = subprocess.run(
        ["git", "show", f"{revision}:hydra-umc.project.json"],
        cwd=str(path),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ManifestValidationError("candidate revision has no readable hydra-umc.project.json")
    return _validated_manifest_text(result.stdout, entry)


def clone_or_pull(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    verify_build: bool = True,
    progress: ProgressCallback | None = None,
) -> InstallResult:
    """git clone if this project isn't checked out yet under
    workspace_root, otherwise `git -C <path> fetch` followed by a real
    `git merge --ff-only FETCH_HEAD` - never a force-push-style reset.
    Before that fast-forward, the updater validates the fetched revision's
    repository-owned manifest and rejects a lower version, so an update
    cannot silently become a rollback. A real local edit a developer made
    (this tool is meant to also run on a dev machine, not only the real
    CM5) fails loudly instead of being silently discarded - explicitly
    checked upfront (see _tracked_dirty_paths()'s own docstring for why
    this can no longer be left to git's own `merge --ff-only` error:
    that used to be true, but stopped being true the moment verify_build
    defaulted to the isolated staging-clone flow below, V07-001).

    UPD-01 (found in an ecosystem-wide software-improvements audit, P1):
    updating an EXISTING checkout used to merge the candidate straight
    into `path`, then leave building it to a separate step
    (install_or_update's own run_build_script call) - a build failure
    there left new sources merged into `path` sitting next to the
    PREVIOUS build's artifacts, an inconsistent install with no rollback.
    With verify_build=True (the default), the candidate is instead
    cloned+merged+built in a fully independent staging clone FIRST -
    `path` is never touched at all until that build actually succeeds -
    then promoted into place via two back-to-back directory renames
    (each individually atomic on the same filesystem; the previous
    installation is kept, not deleted, at `<name>.backup`, so an
    operator can restore it by hand if the new version misbehaves
    despite building fine). A build failure - or a crash, full disk, or
    diverged/dirty checkout at any point before that final promotion -
    leaves `path` completely untouched and still the operative
    installation. verify_build=False skips all of this and restores the
    exact old in-place-merge behavior, for a caller that intentionally
    doesn't want a build (matching install_or_update's own `build=False`
    path)."""
    path = workspace_root / entry.name
    _checkpoint(progress, "preflight", "Validating the selected workspace and project manifest.")
    if not path.exists():
        # Clone to a sibling staging path first.  A failed network transfer or
        # malformed remote must not leave a partial directory that the next
        # operator run mistakes for a real installation.  rename() is atomic
        # inside workspace_root and we never remove a path we did not create.
        staging_path = workspace_root / f".{entry.name}.clone-{uuid4().hex}"
        _checkpoint(progress, "source", "Cloning the selected repository into a safe staging directory.")
        result = _run(
            ["git", "clone", github_repo_url(entry), str(staging_path)],
            cwd=workspace_root,
            capture_output=progress is not None,
        )
        if result.returncode != 0:
            rmtree(staging_path, ignore_errors=True)
            return InstallResult(False, f"git clone failed (exit {result.returncode})", _command_output(result))
        try:
            _checkpoint(progress, "validation", "Validating the fetched repository manifest before deployment.")
            _manifest_from_revision(staging_path, "HEAD", entry)
        except ManifestValidationError as exc:
            rmtree(staging_path, ignore_errors=True)
            return InstallResult(False, f"cloned checkout failed manifest validation: {exc}")
        if path.exists():
            rmtree(staging_path, ignore_errors=True)
            return InstallResult(False, f"{path} appeared while cloning - not replacing it")
        staging_path.replace(path)
        _checkpoint(progress, "validation", "Manifest accepted; staged checkout promoted without replacing other files.")
        return InstallResult(True, f"Cloned into {path}")

    if not (path / ".git").is_dir():
        return InstallResult(False, f"{path} exists but isn't a git checkout - not touching it")

    try:
        _checkpoint(progress, "preflight", "Validating the installed repository manifest.")
        installed = _manifest_from_revision(path, "HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"installed checkout failed manifest validation: {exc}")

    # V07-001: refuse upfront, before any fetch/staging work, if a real
    # tracked file has a genuine uncommitted edit - see
    # _tracked_dirty_paths()'s own docstring for exactly why the
    # staging-clone flow below can no longer be trusted to catch this
    # itself. Applies to both verify_build values - a caller intending
    # the older in-place-merge path (verify_build=False) never wanted
    # a real local edit silently discarded either.
    dirty = _tracked_dirty_paths(path)
    if dirty:
        preview = ", ".join(dirty[:5]) + (f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else "")
        return InstallResult(
            False,
            f"{path} has uncommitted change(s) to real tracked file(s): {preview} - refusing to update; "
            "commit, stash, or discard them first so an update can never silently discard real local work",
        )

    # Fetch first and inspect FETCH_HEAD before changing the operator's
    # working tree. This prevents a malformed or older remote manifest from
    # becoming an installed downgrade merely because Git can fast-forward it.
    _checkpoint(progress, "source", "Fetching the remote candidate without changing the local checkout.")
    result = _run(
        ["git", "fetch", "--quiet", "origin", "HEAD"],
        cwd=path,
        capture_output=progress is not None,
    )
    if result.returncode != 0:
        return InstallResult(
            False,
            f"git fetch failed (exit {result.returncode}) - remote unavailable or authentication failed?",
            _command_output(result),
        )
    try:
        _checkpoint(progress, "validation", "Checking the candidate manifest and anti-rollback rule.")
        candidate = _manifest_from_revision(path, "FETCH_HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"remote candidate failed manifest validation: {exc}")
    if _version_tuple(candidate) < _version_tuple(installed):
        return InstallResult(
            False,
            f"remote candidate v{candidate.version} is older than installed v{installed.version}; anti-rollback refused update",
        )

    if not verify_build:
        _checkpoint(progress, "validation", "Applying the accepted candidate with a fast-forward-only merge.")
        result = _run(
            ["git", "merge", "--ff-only", "FETCH_HEAD"],
            cwd=path,
            capture_output=progress is not None,
        )
        if result.returncode != 0:
            return InstallResult(
                False,
                f"git merge --ff-only failed (exit {result.returncode}) - local changes or a diverged branch?",
                _command_output(result),
            )
        return InstallResult(True, f"Pulled latest into {path}")

    # UPD-01: prove the candidate actually builds in a fully independent
    # staging clone BEFORE touching `path` at all - see this function's
    # own docstring. Resolved as a real SHA (not the name "FETCH_HEAD",
    # which means something different in every repo) BEFORE staging even
    # exists: `path`'s FETCH_HEAD already names this exact commit, and
    # `git clone --local` below copies `path`'s whole object database, so
    # that commit is already a real, present object in the staging clone
    # even though nothing there points to it yet - no second fetch
    # needed, and no dependency on staging's own "origin" (which `git
    # clone` would otherwise point at `path` itself, not path's real
    # upstream - fetching "origin" there would silently fetch nothing
    # new and validate the WRONG, stale candidate).
    candidate_sha = subprocess.run(
        ["git", "rev-parse", "FETCH_HEAD"], cwd=str(path), check=False, capture_output=True, text=True
    ).stdout.strip()
    if not candidate_sha:
        return InstallResult(False, f"could not resolve the fetched candidate to a real commit; {path} was not modified")

    staging_path = workspace_root / f".{entry.name}.update-{uuid4().hex}"
    _checkpoint(progress, "source", "Cloning the installed checkout into an isolated staging area for verification.")
    # --no-hardlinks: a plain `git clone --local` hardlinks object files
    # from `path` on the same volume by default - real, reproducible
    # testing on Windows found that a build script running INSIDE the
    # staging clone can leave those hardlinked objects genuinely
    # undeletable afterward (WinError 5, not a transient lock - retrying
    # does not help), silently leaving an orphaned `.{name}.update-*`
    # directory behind in workspace_root forever. A full copy costs a
    # little more local disk I/O (still no network - this is a same-
    # filesystem clone either way) in exchange for staging actually being
    # a fully independent directory that can always be cleaned up.
    result = _run(
        ["git", "clone", "--local", "--no-hardlinks", str(path), str(staging_path)],
        cwd=workspace_root,
        capture_output=progress is not None,
    )
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"could not create a staging clone for verification (exit {result.returncode}); {path} was not modified",
            _command_output(result),
        )

    # REV-001 (found in an independent revalidation audit, P1): `git
    # clone --local` above points the new clone's own `origin` remote at
    # the LOCAL SOURCE PATH it was cloned from (`path`, the installation
    # about to be renamed aside) - never at this project's real GitHub
    # upstream. Left uncorrected, the checkout this staging clone becomes
    # once promoted below would have `origin` pointing at itself, so
    # every FUTURE `git fetch origin` here would fetch nothing new,
    # silently and permanently stopping this checkout from ever
    # discovering a real update again. Reset to the real upstream
    # immediately, before build/promotion, so staging is a faithful
    # preview of the checkout it is about to become in every respect,
    # not just source content.
    real_origin_url = github_repo_url(entry)
    result = _run(["git", "remote", "set-url", "origin", real_origin_url], cwd=staging_path, capture_output=progress is not None)
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"could not restore the real upstream remote on the staging clone (exit {result.returncode}); {path} was not modified",
            _command_output(result),
        )

    # REV-002 (found in an independent revalidation audit, P1): carry
    # over the installed checkout's own real local data BEFORE building/
    # promoting - see _carry_over_local_data()'s own docstring for the
    # real gap this closes. Done before the build below (not merely
    # before promotion) so a build-test script that reads this project's
    # own real local files during verification sees the same real data
    # the promoted checkout will actually run against.
    _carry_over_local_data(path, staging_path, progress=progress)

    _checkpoint(progress, "validation", "Applying the accepted candidate in the isolated staging clone.")
    result = _run(["git", "merge", "--ff-only", candidate_sha], cwd=staging_path, capture_output=progress is not None)
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"git merge --ff-only failed (exit {result.returncode}) in a staging clone - local changes or a diverged branch? {path} was not modified.",
            _command_output(result),
        )

    _checkpoint(progress, "build", "Building and verifying the candidate in isolation before touching the live installation.")
    build_result = _run_build_script_at(staging_path, progress=progress)
    if not build_result.ok:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"candidate build failed - {path} was left completely untouched and remains the operative installation: {build_result.message}",
            build_result.output,
        )

    # The one real promotion step: swap the previous installation aside
    # (kept, never deleted - see this function's own docstring) and move
    # the proven-buildable staging clone into its place. Both are plain
    # directory renames on the same filesystem/volume, so each one
    # individually is atomic; the only remaining unsafe window is the
    # brief gap between these two renames (a crash exactly there would
    # leave `path` genuinely missing) - vastly narrower than before,
    # where the unsafe window spanned the entire build.
    #
    # V07-004 (found in an independent revalidation audit, P1; honest,
    # bounded mitigation, not the full transactional journal/rollback
    # the finding's own acceptance criteria describes - that needs
    # designing once, shared with HYDRA-UMC-OPS-AGENT's own
    # canary_deploy.py, as real, separate future work): two real gaps
    # existed here. First, `backup_path` reused the SAME fixed name
    # every promotion (`rmtree(backup_path, ...)` right before renaming
    # into it) - a second install after a first one already failed
    # partway would silently delete the ONLY recoverable copy of the
    # previous installation before even attempting the new promotion.
    # Now unique per attempt (`.backup-<uuid>`, matching OPS-AGENT's own
    # fix), never overwriting an earlier backup. Second, a crash or
    # exception in the narrow gap between the two renames used to leave
    # NO active checkout at `path` at all, with no attempt to recover -
    # now a best-effort self-heal: if the second rename fails, this
    # immediately tries to rename the backup back to `path` so a real
    # installation still exists, rather than silently leaving neither a
    # live checkout nor a clear indication of which path holds the real
    # one.
    backup_path = workspace_root / f"{entry.name}.backup-{uuid4().hex[:8]}"
    _checkpoint(progress, "validation", "Promoting the verified candidate; the previous installation is kept as a backup.")
    path.rename(backup_path)
    try:
        staging_path.rename(path)
    except OSError as exc:
        try:
            backup_path.rename(path)
        except OSError:
            return InstallResult(
                False,
                f"promotion failed AND the self-heal restore also failed - {path} may not exist right now; "
                f"the previous installation should still be recoverable at {backup_path}: {exc}",
                build_result.output,
            )
        return InstallResult(
            False,
            f"promotion failed (exit path unavailable: {exc}) - restored the previous installation at {path}; "
            f"the verified candidate is still available at {staging_path} for manual inspection",
            build_result.output,
        )
    sha_label = candidate_sha[:12]
    return InstallResult(
        True,
        f"Updated {path} to v{candidate.version} (commit {sha_label}) after a verified build; "
        f"previous installation kept at {backup_path}",
        build_result.output,
    )


def find_build_test_script(path: Path) -> Path | None:
    import os
    name = BUILD_TEST_SCRIPT_WINDOWS if os.name == "nt" else BUILD_TEST_SCRIPT_POSIX
    candidate = path / name
    return candidate if candidate.is_file() else None


def run_build_script(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    progress: ProgressCallback | None = None,
) -> InstallResult:
    return _run_build_script_at(workspace_root / entry.name, progress=progress)


def _run_build_script_at(path: Path, *, progress: ProgressCallback | None = None) -> InstallResult:
    """The real work behind run_build_script(), taking an explicit path
    instead of deriving one from workspace_root/entry.name - shared with
    clone_or_pull's own staging-clone build verification (UPD-01), which
    needs to build a candidate sitting in a temporary staging directory,
    not (yet) the real installed checkout."""
    script = find_build_test_script(path)
    if script is None:
        return InstallResult(False, f"No non-versioning build-test.sh/.bat found in {path} - upgrade this checkout or verify it manually before deployment.")

    if os.name == "nt":
        cmd = ["cmd", "/c", str(script)]
    else:
        cmd = ["bash", str(script)]

    _checkpoint(progress, "build", f"Running {script.name}; this never increments the project version.")
    result = _run(cmd, cwd=path, capture_output=progress is not None)
    if result.returncode != 0:
        return InstallResult(
            False,
            f"{script.name} exited with code {result.returncode} - see the in-window evidence below for what failed.",
            _command_output(result),
        )
    return InstallResult(True, f"{script.name} completed successfully.", _command_output(result))


def install_or_update(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    build: bool = True,
    progress: ProgressCallback | None = None,
) -> list[InstallResult]:
    """The full manual install/update flow for ONE project - never called
    for more than one project per invocation (see cli.py's own `install`/
    `update` subcommands, which always take an explicit project name, and
    this project's own README for why that is a deliberate, non-optional
    design choice: explicit operator approval keeps deployment safe).

    UPD-01: updating an EXISTING checkout now builds/verifies the
    candidate itself, inside clone_or_pull's own staging clone, BEFORE
    ever promoting it into the real installation - see that function's
    own docstring. A brand-new clone has no previous installation to
    protect, so it still gets its separate run_build_script call here,
    exactly as before."""
    was_existing_checkout = (workspace_root / entry.name / ".git").is_dir()
    results = [clone_or_pull(entry, workspace_root, verify_build=build, progress=progress)]
    if results[0].ok and build and not was_existing_checkout:
        results.append(run_build_script(entry, workspace_root, progress=progress))
    elif results[0].ok and build:
        _checkpoint(progress, "build", "Build already verified in an isolated staging clone before promotion.")
    elif results[0].ok:
        _checkpoint(progress, "build", "Build-test was deliberately skipped for this one approved source refresh.")
    return results


def _command_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return compact child evidence when a GUI captured it.

    The full command output remains available in the process result while the
    desktop surface keeps a bounded, readable activity trace instead of
    attempting to render an unbounded compiler log.
    """
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
