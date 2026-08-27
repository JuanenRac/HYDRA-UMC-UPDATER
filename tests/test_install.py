# =============================================================================
# HYDRA-UMC-UPDATER - Safe install/update behavior tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from hydra_umc_updater import install
from hydra_umc_updater.install import clone_or_pull, find_build_test_script
from hydra_umc_updater.registry import ProjectEntry


def entry() -> ProjectEntry:
    return ProjectEntry("HYDRA-UMC-EXAMPLE", "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)")


def test_prefers_the_non_versioning_build_test_script(tmp_path: Path):
    project = tmp_path / entry().name
    project.mkdir()
    expected = project / ("build-test.bat" if os.name == "nt" else "build-test.sh")
    expected.write_text("build test\n", encoding="utf-8")
    (project / "build.sh").write_text("versioned build\n", encoding="utf-8")

    assert find_build_test_script(project) == expected


def test_never_touches_an_existing_non_git_directory(tmp_path: Path):
    project = tmp_path / entry().name
    project.mkdir()
    sentinel = project / "operator-file.txt"
    sentinel.write_text("must remain untouched", encoding="utf-8")

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "isn't a git checkout" in result.message
    assert sentinel.read_text(encoding="utf-8") == "must remain untouched"


def test_missing_build_test_fails_closed(tmp_path: Path):
    project = tmp_path / entry().name
    project.mkdir()

    assert find_build_test_script(project) is None


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_failed_clone_removes_only_its_staging_directory(tmp_path: Path, monkeypatch):
    missing_remote = tmp_path / "does-not-exist.git"
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(missing_remote))

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert not (tmp_path / entry().name).exists()
    assert not list(tmp_path.glob(f".{entry().name}.clone-*"))


def test_diverged_pull_fails_without_resetting_local_checkout(tmp_path: Path):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    (seed / "state.txt").write_text("base\n", encoding="utf-8")
    git("add", "state.txt", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=local)
    git("config", "user.name", "Contract", cwd=local)
    (local / "state.txt").write_text("local\n", encoding="utf-8")
    git("commit", "-am", "local", cwd=local)
    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()

    (seed / "state.txt").write_text("remote\n", encoding="utf-8")
    git("commit", "-am", "remote", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "pull --ff-only failed" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == local_head
    assert (local / "state.txt").read_text(encoding="utf-8") == "local\n"
