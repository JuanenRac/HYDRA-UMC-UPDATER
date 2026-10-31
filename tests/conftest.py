# =============================================================================
# HYDRA-UMC-UPDATER - Shared test fixtures
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from pathlib import Path

import pytest

from hydra_umc_updater import install, settings
from train_helpers import SimRepo, entry_for


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keeps every test away from the real settings file of whoever runs it, so a
    saved language, workspace or signature requirement never changes a result."""
    path = tmp_path_factory.mktemp("settings") / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    monkeypatch.delenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED", raising=False)
    for name in ("HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS", "HYDRA_UMC_UPDATER_TRAIN_PUBKEY", "HYDRA_UMC_UPDATER_TRAIN_KEY_FILE"):
        monkeypatch.delenv(name, raising=False)
    # no test writes the ETag cache of whoever runs it
    monkeypatch.setenv("HYDRA_UMC_UPDATER_NO_CACHE", "1")
    return path


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Simulated local projects (a bare remote each) installed through `file` paths, no network."""
    repos: dict[str, SimRepo] = {}
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(install, "github_repo_url", lambda entry: str(repos[entry.name].remote))

    class World:
        pass

    w = World()
    w.workspace = workspace  # type: ignore[attr-defined]
    w.repos = repos  # type: ignore[attr-defined]

    def make(name: str, *versions: str, depends_on: tuple[str, ...] = ()) -> SimRepo:
        repo = SimRepo(name, tmp_path, depends_on).create()
        for version in versions:
            repo.publish(version)
        repos[name] = repo
        return repo

    w.make = make  # type: ignore[attr-defined]

    def entries(*names: str) -> dict:
        return {name: entry_for(name, repos[name].depends_on) for name in names}

    w.entries = entries  # type: ignore[attr-defined]
    return w
