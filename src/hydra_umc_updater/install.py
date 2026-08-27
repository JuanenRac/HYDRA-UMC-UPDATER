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
from shutil import rmtree
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .registry import ProjectEntry, github_repo_url

# Checked in this order - the first one that exists in the checkout is the
# one actually run. Covers every real name used across the 44 projects
# (see this module's own header comment) without needing a per-project
# override in registry.py for something this mechanical.
BUILD_TEST_SCRIPT_POSIX = "build-test.sh"
BUILD_TEST_SCRIPT_WINDOWS = "build-test.bat"


@dataclass
class InstallResult:
    ok: bool
    message: str


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), check=False)


def clone_or_pull(entry: ProjectEntry, workspace_root: Path) -> InstallResult:
    """git clone if this project isn't checked out yet under
    workspace_root, otherwise `git -C <path> pull --ff-only` - never a
    force-push-style reset, so a real local edit a developer made (this
    tool is meant to also run on a dev machine, not only the real CM5)
    fails loudly with git's own error instead of being silently
    discarded."""
    path = workspace_root / entry.name
    if not path.exists():
        # Clone to a sibling staging path first.  A failed network transfer or
        # malformed remote must not leave a partial directory that the next
        # operator run mistakes for a real installation.  rename() is atomic
        # inside workspace_root and we never remove a path we did not create.
        staging_path = workspace_root / f".{entry.name}.clone-{uuid4().hex}"
        result = _run(["git", "clone", github_repo_url(entry), str(staging_path)], cwd=workspace_root)
        if result.returncode != 0:
            rmtree(staging_path, ignore_errors=True)
            return InstallResult(False, f"git clone failed (exit {result.returncode})")
        if path.exists():
            rmtree(staging_path, ignore_errors=True)
            return InstallResult(False, f"{path} appeared while cloning - not replacing it")
        staging_path.replace(path)
        return InstallResult(True, f"Cloned into {path}")

    if not (path / ".git").is_dir():
        return InstallResult(False, f"{path} exists but isn't a git checkout - not touching it")

    result = _run(["git", "pull", "--ff-only"], cwd=path)
    if result.returncode != 0:
        return InstallResult(False, f"git pull --ff-only failed (exit {result.returncode}) - local changes or a diverged branch?")
    return InstallResult(True, f"Pulled latest into {path}")


def find_build_test_script(path: Path) -> Path | None:
    import os
    name = BUILD_TEST_SCRIPT_WINDOWS if os.name == "nt" else BUILD_TEST_SCRIPT_POSIX
    candidate = path / name
    return candidate if candidate.is_file() else None


def run_build_script(entry: ProjectEntry, workspace_root: Path) -> InstallResult:
    path = workspace_root / entry.name
    script = find_build_test_script(path)
    if script is None:
        return InstallResult(False, f"No non-versioning build-test.sh/.bat found in {path} - upgrade this checkout or verify it manually before deployment.")

    import os
    if os.name == "nt":
        cmd = ["cmd", "/c", str(script)]
    else:
        cmd = ["bash", str(script)]

    result = _run(cmd, cwd=path)
    if result.returncode != 0:
        return InstallResult(False, f"{script.name} exited with code {result.returncode} - see its own output above for what failed.")
    return InstallResult(True, f"{script.name} completed successfully.")


def install_or_update(entry: ProjectEntry, workspace_root: Path, *, build: bool = True) -> list[InstallResult]:
    """The full manual install/update flow for ONE project - never called
    for more than one project per invocation (see cli.py's own `install`/
    `update` subcommands, which always take an explicit project name, and
    this project's own README for why that is a deliberate, non-optional
    design choice: explicit operator approval keeps deployment safe)."""
    results = [clone_or_pull(entry, workspace_root)]
    if results[0].ok and build:
        results.append(run_build_script(entry, workspace_root))
    return results
