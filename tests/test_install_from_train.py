# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_install_from_train.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""With install_from_train on, install and update take the commit and version of the version train, not the latest release of each repository."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_umc_updater import install, settings
from hydra_umc_updater.install import install_or_update
from hydra_umc_updater.install import resolve_release_pin as real_resolve_release_pin
from hydra_umc_updater.release_channel import ReleaseError


def write_train(path: Path, rows: list[tuple[str, str, str]]) -> None:
    path.write_text(json.dumps({
        "schema_version": "1.0", "ecosystem": "HYDRA-UMC",
        "repositories": [{"name": n, "version": v, "commit": c} for n, v, c in rows],
    }), encoding="utf-8")


@pytest.fixture
def train_world(world, monkeypatch, tmp_path):
    monkeypatch.setattr(install, "resolve_release_pin", real_resolve_release_pin)
    monkeypatch.setenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS", "0")
    train_file = tmp_path / "train.json"
    settings.save_install_from_train(True, str(train_file))
    return world, train_file


def version_of(path: Path) -> str:
    return json.loads((path / "hydra-umc.project.json").read_text(encoding="utf-8"))["version"]


def test_it_is_off_by_default_and_a_damaged_file_keeps_it_off(isolated_settings: Path) -> None:
    assert settings.get_install_from_train() is False
    settings.save_install_from_train(True, "/x/train.json")
    assert settings.get_install_from_train() is True and settings.get_train_file() == "/x/train.json"
    isolated_settings.write_text("{not json", encoding="utf-8")
    assert settings.get_install_from_train() is False


def test_a_first_install_gets_the_version_of_the_train_and_not_the_head(train_world) -> None:
    world, train_file = train_world
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0", "0.2.0", "0.3.0")
    write_train(train_file, [("HYDRA-UMC-DEMO", "0.2.0", repo.commits["0.2.0"])])
    results = install_or_update(world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"], world.workspace)
    assert all(r.ok for r in results), [r.message for r in results]
    assert version_of(world.workspace / "HYDRA-UMC-DEMO") == "0.2.0"


def test_a_repository_the_train_does_not_list_installs_nothing(train_world) -> None:
    world, train_file = train_world
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0")
    other = world.make("HYDRA-UMC-OTHER", "0.1.0")
    write_train(train_file, [("HYDRA-UMC-DEMO", "0.1.0", repo.commits["0.1.0"])])
    results = install_or_update(world.entries("HYDRA-UMC-OTHER")["HYDRA-UMC-OTHER"], world.workspace)
    assert not all(r.ok for r in results)
    assert "not listed in the version train" in " ".join(r.message for r in results)
    assert not (world.workspace / "HYDRA-UMC-OTHER").exists()
    assert other.commits


def test_a_commit_that_is_not_the_version_it_claims_is_refused(train_world) -> None:
    world, train_file = train_world
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0", "0.2.0")
    write_train(train_file, [("HYDRA-UMC-DEMO", "0.2.0", repo.commits["0.1.0"])])
    results = install_or_update(world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"], world.workspace)
    assert not all(r.ok for r in results)
    assert not (world.workspace / "HYDRA-UMC-DEMO").exists()


def test_the_train_must_be_signed_unless_the_operator_said_otherwise(train_world, monkeypatch) -> None:
    world, train_file = train_world
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0")
    write_train(train_file, [("HYDRA-UMC-DEMO", "0.1.0", repo.commits["0.1.0"])])
    monkeypatch.delenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS")
    results = install_or_update(world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"], world.workspace)
    assert not all(r.ok for r in results)
    assert "signature" in " ".join(r.message for r in results)
    assert not (world.workspace / "HYDRA-UMC-DEMO").exists()


def test_without_a_train_file_nothing_is_installed(train_world) -> None:
    world, train_file = train_world
    world.make("HYDRA-UMC-DEMO", "0.1.0")
    settings.save_install_from_train(True, "")
    entry = world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"]
    with pytest.raises(ReleaseError):
        real_resolve_release_pin(entry)
