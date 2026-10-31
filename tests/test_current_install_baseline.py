# =============================================================================
# HYDRA-UMC-UPDATER - Characterization of the current install/update (HEAD of every repository)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Fixes how install and update behave today, with temporary Git repositories: a new install takes the head of the
remote, an update moves to the head, an older head is refused, and a batch follows depends_on. Whatever is added on top
(version trains) must leave every one of these results unchanged when it is switched off."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydra_umc_updater import install
from hydra_umc_updater.install import install_or_update, order_batch
from train_helpers import SimRepo, checkout_head, entry_for


@pytest.fixture
def sim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repos: dict[str, SimRepo] = {}
    (tmp_path / "ws").mkdir()
    monkeypatch.setattr(install, "github_repo_url", lambda entry: str(repos[entry.name].remote))

    def make(name: str, *versions: str, depends_on: tuple[str, ...] = ()) -> SimRepo:
        repo = SimRepo(name, tmp_path, depends_on).create()
        for version in versions:
            repo.publish(version)
        repos[name] = repo
        return repo

    make.workspace = tmp_path / "ws"  # type: ignore[attr-defined]
    return make


def test_a_new_install_takes_the_head_of_the_remote(sim):
    repo = sim("HYDRA-UMC-AAA", "1.0.0", "1.1.0")
    results = install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace)
    assert all(r.ok for r in results), [r.message for r in results]
    assert checkout_head(sim.workspace, "HYDRA-UMC-AAA") == repo.commits["1.1.0"]
    assert (sim.workspace / "HYDRA-UMC-AAA" / "built.txt").exists()


def test_an_update_moves_to_the_new_head(sim):
    repo = sim("HYDRA-UMC-AAA", "1.0.0")
    assert all(r.ok for r in install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace))
    repo.publish("1.2.0")
    results = install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace)
    assert all(r.ok for r in results), [r.message for r in results]
    assert checkout_head(sim.workspace, "HYDRA-UMC-AAA") == repo.commits["1.2.0"]


def test_an_update_never_goes_back_to_an_older_version(sim):
    repo = sim("HYDRA-UMC-AAA", "1.0.0")
    assert all(r.ok for r in install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace))
    repo.publish("1.2.0")
    assert all(r.ok for r in install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace))
    repo.publish("1.1.0")  # the remote head now carries a lower version than the one installed
    results = install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace)
    assert not all(r.ok for r in results)
    assert "anti-rollback" in " ".join(r.message for r in results)


def test_a_failed_build_leaves_the_installation_as_it_was(sim):
    repo = sim("HYDRA-UMC-AAA", "1.0.0")
    assert all(r.ok for r in install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace))
    before = checkout_head(sim.workspace, "HYDRA-UMC-AAA")
    repo.publish("1.1.0", build_ok=False)
    results = install_or_update(entry_for("HYDRA-UMC-AAA"), sim.workspace)
    assert not all(r.ok for r in results)
    assert checkout_head(sim.workspace, "HYDRA-UMC-AAA") == before


def test_the_batch_follows_depends_on():
    names = ["HYDRA-UMC-AAA", "HYDRA-UMC-BBB", "HYDRA-UMC-SDK"]
    assert order_batch(names, {"HYDRA-UMC-AAA": ["HYDRA-UMC-BBB"]}) == ["HYDRA-UMC-SDK", "HYDRA-UMC-BBB", "HYDRA-UMC-AAA"]
