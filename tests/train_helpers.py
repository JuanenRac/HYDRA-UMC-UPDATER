# =============================================================================
# HYDRA-UMC-UPDATER - Local simulated repositories for the install and train tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Temporary Git repositories with a manifest and a build script, no network: a bare "remote" per project that a
test pushes releases to, so installs and updates run the real code against `file` paths."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from hydra_umc_updater.registry import ProjectEntry


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def entry_for(name: str, depends_on: tuple[str, ...] = ()) -> ProjectEntry:
    return ProjectEntry(name, "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)", depends_on=depends_on)


@dataclass
class SimRepo:
    """One simulated project: a bare remote plus the working copy used to publish to it."""

    name: str
    root: Path
    depends_on: tuple[str, ...] = ()
    commits: dict[str, str] = field(default_factory=dict)  # version -> full commit id

    @property
    def remote(self) -> Path:
        return self.root / "remotes" / f"{self.name}.git"

    @property
    def seed(self) -> Path:
        return self.root / "seeds" / self.name

    def create(self) -> SimRepo:
        git("init", "--bare", "-b", "main", str(self.remote), cwd=self.root)
        git("clone", str(self.remote), str(self.seed), cwd=self.root)
        git("config", "user.email", "sim@example.invalid", cwd=self.seed)
        git("config", "user.name", "Sim", cwd=self.seed)
        return self

    def publish(self, version: str, *, build_ok: bool = True, depends_on: tuple[str, ...] | None = None) -> str:
        deps = self.depends_on if depends_on is None else depends_on
        manifest = {
            "schema_version": "1.0",
            "ecosystem": "HYDRA-UMC",
            "name": self.name,
            "version": version,
            "role": "service",
            "stack": "python",
            "technologies": ["Python"],
            "deployment_target": "cm5",
            "maturity": "functional",
            "family": "Test",
            "parent": None,
            "native_version": {"file": "pyproject.toml", "pattern": "(\\d+)\\.(\\d+)\\.(\\d+)"},
            "build": "python -m compileall src",
            "notes": "Test manifest.",
        }
        if deps:
            manifest["depends_on"] = list(deps)
        (self.seed / "hydra-umc.project.json").write_text(json.dumps(manifest), encoding="utf-8")
        if build_ok:
            (self.seed / "build-test.sh").write_text("#!/usr/bin/env bash\necho built > built.txt\nexit 0\n", encoding="utf-8")
            (self.seed / "build-test.bat").write_text("@echo off\r\necho built> built.txt\r\nexit /b 0\r\n", encoding="utf-8")
        else:
            (self.seed / "build-test.sh").write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            (self.seed / "build-test.bat").write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")
        git("add", "-A", cwd=self.seed)
        git("commit", "-m", f"release {version}", cwd=self.seed)
        git("push", "origin", "HEAD:main", cwd=self.seed)
        commit = git("rev-parse", "HEAD", cwd=self.seed)
        self.commits[version] = commit
        return commit

    def head(self) -> str:
        return git("rev-parse", "HEAD", cwd=self.seed)


def checkout_head(workspace: Path, name: str) -> str:
    return git("rev-parse", "HEAD", cwd=workspace / name)
