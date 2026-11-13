# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_simulation_bench.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Simulation bench: the real release resolver and the real plan applier run against a simulated GitHub and a simulated device.

Everything is seeded. The simulated API drops, times out, answers with garbage or serves a tag that points nowhere; the simulated
device refuses, rolls back or fails a step. The invariants checked are the safety ones: a resolver never returns a draft, a pre-release
on the stable channel or an unordered tag; a plan applier never deploys without the confirmation and the switch, stops at the first
failed step and deploys nothing after it. Nothing here touches a network or a machine: the evidence is `simulator`, not hardware.
"""
from __future__ import annotations

import random
import re
import urllib.error
from pathlib import Path

import pytest

from hydra_umc_updater import deploy_plan, install
from hydra_umc_updater.release_channel import ReleaseError, resolve_latest

SEEDS = range(300)
SHA = "e" * 40


def make_fleet(rng: random.Random) -> list[dict]:
    releases = []
    for _ in range(rng.randint(0, 10)):
        version = f"{rng.randint(0, 2)}.{rng.randint(0, 12)}.{rng.randint(0, 12)}"
        kind = rng.choice(["plain", "draft", "pre", "junk", "suffix"])
        tag = {"plain": f"v{version}", "draft": f"v{version}", "pre": f"v{version}-rc{rng.randint(1, 3)}", "junk": rng.choice(["latest", "nightly", "v1", ""]), "suffix": f"v{version}-beta"}[kind]
        releases.append({"tag_name": tag, "draft": kind == "draft", "prerelease": kind == "pre", "assets": []})
    rng.shuffle(releases)
    return releases


def key(tag: str) -> tuple[int, ...]:
    parts = tag.lstrip("v").split(".")
    return tuple(int(p) for p in parts) + (0,) * (4 - len(parts))


def flaky_api(rng: random.Random, releases: list[dict], fault: str | None):
    def fetch(url: str):
        if fault == "list-down" and "/releases?" in url:
            raise urllib.error.URLError("connection reset")
        if fault == "list-garbage" and "/releases?" in url:
            return rng.choice([{}, "oops", None, 12])
        if "/releases?" in url:
            return releases
        if fault == "tag-timeout":
            raise TimeoutError("slow")
        if fault == "tag-nowhere":
            return {"object": {"type": "commit", "sha": "zz"}}
        return {"object": {"type": "commit", "sha": SHA}}

    return fetch


@pytest.mark.parametrize("channel", ["stable", "pruebas"])
def test_the_resolver_keeps_its_promises_under_seeded_faults(channel: str) -> None:
    chosen = failed = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        releases = make_fleet(rng)
        fault = rng.choice([None, None, None, "list-down", "list-garbage", "tag-timeout", "tag-nowhere"])
        try:
            info = resolve_latest("HYDRA-UMC-SIM", channel, fetch=flaky_api(rng, releases, fault))
        except ReleaseError as error:
            failed += 1
            assert error.code in {"unreachable", "bad_answer", "none"}, (seed, error.code)
            continue
        chosen += 1
        assert fault is None, (seed, fault)
        assert info.commit == SHA
        allowed = [
            r for r in releases
            if not r["draft"] and re.fullmatch(r"v\d+\.\d+\.\d+", r["tag_name"]) or (channel == "pruebas" and r["prerelease"] and re.fullmatch(r"v\d+\.\d+\.\d+-rc\d", r["tag_name"]))
        ]
        allowed = [r for r in allowed if not r["draft"]]
        assert any(r["tag_name"] == info.tag for r in allowed), (seed, info.tag)
        best = max(key(r["tag_name"].lstrip("v").split("-")[0]) for r in allowed)
        assert key(info.version) == best, (seed, info.tag)
        if channel == "stable":
            assert not info.prerelease
    assert chosen > 20 and failed > 20  # the seeds really exercise both outcomes


def scripted_device(statuses: list[str], called: list[str]):
    def device(project: str) -> install.OsDeployOutcome:
        called.append(project)
        return install.OsDeployOutcome(statuses[len(called) - 1], "simulated")

    return device


def scripted_verifier(good_until: int):
    seen: list[str] = []

    def verify(checkout: Path) -> tuple[bool, str]:
        seen.append(checkout.name)
        return (len(seen) <= good_until, "simulated signature check")

    return verify


def plan_of(count: int) -> deploy_plan.DeployPlan:
    rows = [
        deploy_plan.PlanRow(f"HYDRA-UMC-P{i}", deploy_plan.DEPLOY, "2.0.0", "1.0.0", None, None, None, "older on the device")
        for i in range(count)
    ]
    return deploy_plan.DeployPlan(rows)


def test_the_applier_stops_at_the_first_failure_for_every_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(install.OS_DEPLOY_ENV, "1")
    monkeypatch.delenv(install.REQUIRE_SIGNED_ENV, raising=False)
    for seed in SEEDS:
        rng = random.Random(seed)
        count = rng.randint(1, 8)
        statuses = [rng.choice(["deployed", "deployed", "deployed", "refused", "rolled-back", "failed", "unavailable"]) for _ in range(count)]
        called: list[str] = []
        device = scripted_device(statuses, called)

        workspace = tmp_path / f"w{seed}"
        workspace.mkdir()
        outcome = deploy_plan.apply_plan(plan_of(count), workspace, confirmed=True, deploy=device)
        first_bad = next((i for i, s in enumerate(statuses) if s != "deployed"), None)
        if first_bad is None:
            assert outcome.ok and len(called) == count, seed
        else:
            assert not outcome.ok, seed
            assert len(called) == first_bad + 1, (seed, statuses, called)
            assert "stopped here" in outcome.messages[-1]


def test_nothing_is_deployed_without_confirmation_or_the_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def device(project: str) -> install.OsDeployOutcome:
        called.append(project)
        return install.OsDeployOutcome("deployed", "simulated")

    rng = random.Random(7)
    for _ in range(50):
        confirmed = rng.random() < 0.5
        switch = rng.choice(["0", "off", "no", "false", "1", "on"])
        monkeypatch.setenv(install.OS_DEPLOY_ENV, switch)
        monkeypatch.delenv(install.REQUIRE_SIGNED_ENV, raising=False)
        before = len(called)
        outcome = deploy_plan.apply_plan(plan_of(2), tmp_path, confirmed=confirmed, deploy=device)
        if confirmed and switch in {"1", "on"}:
            assert outcome.ok and len(called) == before + 2
        else:
            assert not outcome.ok and len(called) == before


def test_a_required_signature_that_fails_stops_every_step(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(install.OS_DEPLOY_ENV, "1")
    monkeypatch.setenv(install.REQUIRE_SIGNED_ENV, "1")
    called: list[str] = []

    def device(project: str) -> install.OsDeployOutcome:
        called.append(project)
        return install.OsDeployOutcome("deployed", "simulated")

    rng = random.Random(99)
    for _ in range(40):
        good_until = rng.randint(0, 4)
        verify = scripted_verifier(good_until)

        called.clear()
        outcome = deploy_plan.apply_plan(plan_of(4), tmp_path, confirmed=True, deploy=device, verify_signature=verify)
        assert len(called) == min(good_until, 4)
        assert outcome.ok == (good_until >= 4)
