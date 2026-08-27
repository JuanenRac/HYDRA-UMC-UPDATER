# =============================================================================
# HYDRA-UMC-UPDATER - Clone/pull + delegate to each project's own build
# script: install.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Deliberately does NOT reimplement per-stack build logic (npm/cargo/go/
# gradlew/flutter/pip, 7 different toolchains across 44 projects) - every
# project in this ecosystem already carries its own real, working
# build.sh/.bat (or a differently-named equivalent - build_firmware.sh for
# the 2 multi-component firmware repos, build_exe.sh for the 4 PyInstaller
# ones, build-android.sh for HYDRA-UMC-ANDROID-CONTROL specifically - see
# BUILD_SCRIPT_CANDIDATES below) that already knows its own real
# dependencies, venv/toolchain setup, and quirks (HYDRA-UMC-TELEMETRY-
# COLLECTOR/HYDRA-UMC-TOOL-CLI's module root being src/, not the repo
# root, for instance). Reimplementing that here would mean two places that
# both claim to know how to build a given project, guaranteed to drift.
# This module's own job ends at "clone/pull the source, then run whichever
# build script this specific checkout actually has."
# =============================================================================
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .registry import ProjectEntry, github_repo_url

# Checked in this order - the first one that exists in the checkout is the
# one actually run. Covers every real name used across the 44 projects
# (see this module's own header comment) without needing a per-project
# override in registry.py for something this mechanical.
BUILD_SCRIPT_CANDIDATES_POSIX = [
    "build.sh", "build_firmware.sh", "build_exe.sh", "build-android.sh",
]
BUILD_SCRIPT_CANDIDATES_WINDOWS = [
    "build.bat", "build_firmware.bat", "build_exe.bat", "build-android.bat",
]


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
        result = _run(["git", "clone", github_repo_url(entry), str(path)], cwd=workspace_root)
        if result.returncode != 0:
            return InstallResult(False, f"git clone failed (exit {result.returncode})")
        return InstallResult(True, f"Cloned into {path}")

    if not (path / ".git").is_dir():
        return InstallResult(False, f"{path} exists but isn't a git checkout - not touching it")

    result = _run(["git", "pull", "--ff-only"], cwd=path)
    if result.returncode != 0:
        return InstallResult(False, f"git pull --ff-only failed (exit {result.returncode}) - local changes or a diverged branch?")
    return InstallResult(True, f"Pulled latest into {path}")


def find_build_script(path: Path) -> Path | None:
    import os
    candidates = BUILD_SCRIPT_CANDIDATES_WINDOWS if os.name == "nt" else BUILD_SCRIPT_CANDIDATES_POSIX
    for name in candidates:
        candidate = path / name
        if candidate.is_file():
            return candidate
    return None


def run_build_script(entry: ProjectEntry, workspace_root: Path) -> InstallResult:
    path = workspace_root / entry.name
    script = find_build_script(path)
    if script is None:
        return InstallResult(False, f"No build.sh/.bat (or a known equivalent) found in {path} - see this project's own README for how to build it manually.")

    import os
    if os.name == "nt":
        cmd = [str(script)]
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
