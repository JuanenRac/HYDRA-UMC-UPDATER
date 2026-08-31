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
from shutil import rmtree
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


def _checkpoint(progress: ProgressCallback | None, phase: str, message: str) -> None:
    if progress is not None:
        progress(phase, message)


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
    progress: ProgressCallback | None = None,
) -> InstallResult:
    """git clone if this project isn't checked out yet under
    workspace_root, otherwise `git -C <path> fetch` followed by a real
    `git merge --ff-only FETCH_HEAD` - never a force-push-style reset.
    Before that fast-forward, the updater validates the fetched revision's
    repository-owned manifest and rejects a lower version, so an update
    cannot silently become a rollback. A real local edit a developer made
    (this tool is meant to also run on a dev machine, not only the real
    CM5) fails loudly with git's own error instead of being silently
    discarded."""
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
    path = workspace_root / entry.name
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
    design choice: explicit operator approval keeps deployment safe)."""
    results = [clone_or_pull(entry, workspace_root, progress=progress)]
    if results[0].ok and build:
        results.append(run_build_script(entry, workspace_root, progress=progress))
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
