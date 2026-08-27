# =============================================================================
# HYDRA-UMC-UPDATER - Safe install/update behavior tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import os
from pathlib import Path

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
