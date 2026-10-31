# =============================================================================
# HYDRA-UMC-UPDATER - Version trains against simulated local repositories
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hydra_umc_updater import install, main, settings, train
from hydra_umc_updater.install import install_or_update
from train_helpers import SimRepo, checkout_head, entry_for, git

SDK, AAA, BBB = "HYDRA-UMC-SDK", "HYDRA-UMC-AAA", "HYDRA-UMC-BBB"
BAD = "f" * 40


def make_train(repos: list[dict[str, object]], **extra: object) -> train.Train:
    data = {"schema_version": "1.0", "ecosystem": "HYDRA-UMC", "repositories": repos, **extra}
    return train.parse_train(json.dumps(data))


def item(repo: SimRepo, version: str, **extra: object) -> dict[str, object]:
    return {"name": repo.name, "version": version, "commit": repo.commits[version], **extra}


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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


# ----------------------------------------------------------------------------- the file ---------------------------

def good_repo(**extra: object) -> dict[str, object]:
    return {"name": AAA, "version": "1.0.0", "commit": "a" * 40, **extra}


def test_the_real_release_file_of_the_family_is_a_train():
    path = Path(__file__).resolve().parents[2] / "HYDRA-UMC-DOCS" / "data" / "ecosystem-release.json"
    if not path.is_file():
        pytest.skip("the documentation checkout is not next to this one")
    loaded = train.load_train(path)
    assert len(loaded.repos) > 10 and all(len(repo.commit) == 40 for repo in loaded.repos)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(schema_version="2.0"),
        lambda d: d.update(ecosystem="URTC"),
        lambda d: d.update(extra=1),
        lambda d: d.update(repositories=[]),
        lambda d: d.update(repositories=[good_repo(), good_repo()]),
        lambda d: d.update(repositories=[good_repo(commit="abc")]),
        lambda d: d.update(repositories=[good_repo(commit="A" * 40)]),
        lambda d: d.update(repositories=[good_repo(version="1.0")]),
        lambda d: d.update(repositories=[good_repo(name="evil")]),
        lambda d: d.update(repositories=[good_repo(surprise=True)]),
        lambda d: d.update(repositories=[good_repo(depends_on=[AAA])]),
        lambda d: d.update(repositories=[good_repo(requires_min={SDK: "x"})]),
        lambda d: d.update(repositories=[good_repo(manifest_sha256="12")]),
        lambda d: d.update(digest="0" * 64),
    ],
)
def test_a_malformed_train_is_refused(mutate):
    data = {"schema_version": "1.0", "ecosystem": "HYDRA-UMC", "repositories": [good_repo()]}
    mutate(data)
    with pytest.raises(train.TrainError):
        train.parse_train(json.dumps(data))


@pytest.mark.parametrize("text", ["", "[]", "{", "null"])
def test_text_that_is_not_a_train_object_is_refused(text):
    with pytest.raises(train.TrainError):
        train.parse_train(text)


def test_the_digest_detects_a_changed_file_and_round_trips():
    original = make_train([good_repo(), {"name": BBB, "version": "2.0.0", "commit": "b" * 40}])
    text = train.train_to_json(original)
    assert train.parse_train(text).repos == original.repos
    tampered = text.replace('"2.0.0"', '"2.0.1"')
    with pytest.raises(train.TrainError, match="digest"):
        train.parse_train(tampered)


# ----------------------------------------------------------------------------- the switch ------------------------

def test_the_switch_is_off_by_default_and_follows_environment_and_settings(monkeypatch):
    monkeypatch.delenv(train.TRAINS_ENV, raising=False)
    assert train.trains_enabled() is False
    settings.save_settings(version_trains=True)
    assert train.trains_enabled() is True
    monkeypatch.setenv(train.TRAINS_ENV, "0")
    assert train.trains_enabled() is False
    monkeypatch.delenv(train.TRAINS_ENV)
    settings.SETTINGS_PATH.write_text("[broken", encoding="utf-8")
    assert train.trains_enabled() is False


# ----------------------------------------------------------------------------- compatibility ---------------------

def test_requirements_and_dependencies_are_checked_before_anything_else(world, tmp_path):
    sdk, aaa = world.make(SDK, "0.3.0"), world.make(AAA, "1.0.0")
    old = make_train([item(sdk, "0.3.0"), item(aaa, "1.0.0", requires_min={SDK: "0.4.0"})])
    plan = train.plan_train(old, world.workspace, fetch=None)
    assert not plan.ok and any("needs HYDRA-UMC-SDK >= 0.4.0" in p for p in plan.problems)

    missing = make_train([item(aaa, "1.0.0", depends_on=[BBB])])
    assert any("depends on HYDRA-UMC-BBB" in p for p in train.plan_train(missing, world.workspace, fetch=None).problems)

    cycle = make_train([item(aaa, "1.0.0", depends_on=[SDK]), item(sdk, "0.3.0", depends_on=[AAA])])
    assert any("cycle" in p for p in train.plan_train(cycle, world.workspace, fetch=None).problems)


def test_the_plan_follows_depends_on_and_explains_each_step(world):
    sdk, aaa, bbb = world.make(SDK, "0.3.0"), world.make(AAA, "1.0.0"), world.make(BBB, "1.0.0")
    t = make_train([item(aaa, "1.0.0", depends_on=[BBB]), item(bbb, "1.0.0", depends_on=[SDK]), item(sdk, "0.3.0")])
    plan = train.plan_train(t, world.workspace, fetch=None)
    assert plan.ok and [i.name for i in plan.items] == [SDK, BBB, AAA]
    text = train.format_plan(plan, dry_run=True)
    assert "Dry run: nothing was installed" in text and "INSTALL" in text and "checked after the clone" in text


# ----------------------------------------------------------------------------- applying -------------------------

def test_a_fresh_install_takes_the_commit_of_the_train_not_the_head(world):
    aaa = world.make(AAA, "1.0.0", "1.1.0", "1.2.0")
    t = make_train([item(aaa, "1.1.0")])
    plan = train.plan_train(t, world.workspace, fetch=None)
    outcome = train.apply_train(plan, world.workspace, world.entries(AAA))
    assert outcome.ok, outcome.messages
    assert checkout_head(world.workspace, AAA) == aaa.commits["1.1.0"]
    assert (world.workspace / AAA / "built.txt").exists()
    # the checkout can still follow the remote afterwards
    result = install_or_update(entry_for(AAA), world.workspace)
    assert all(r.ok for r in result), [r.message for r in result]
    assert checkout_head(world.workspace, AAA) == aaa.commits["1.2.0"]


def test_an_update_goes_to_the_train_and_only_what_differs_is_installed(world):
    sdk, aaa = world.make(SDK, "0.3.0"), world.make(AAA, "1.0.0")
    assert all(r.ok for e in world.entries(SDK, AAA).values() for r in install_or_update(e, world.workspace))
    sdk_before = checkout_head(world.workspace, SDK)
    aaa.publish("1.1.0")
    aaa.publish("1.2.0")
    t = make_train([item(sdk, "0.3.0"), item(aaa, "1.1.0")])
    plan = train.plan_train(t, world.workspace)
    assert {i.name: i.action for i in plan.items} == {SDK: "keep", AAA: "update"}
    outcome = train.apply_train(plan, world.workspace, world.entries(SDK, AAA))
    assert outcome.ok and outcome.applied == [AAA], outcome.messages
    assert checkout_head(world.workspace, AAA) == aaa.commits["1.1.0"]
    assert checkout_head(world.workspace, SDK) == sdk_before


def test_a_failed_check_in_the_plan_installs_nothing(world):
    aaa = world.make(AAA, "1.0.0")
    assert all(r.ok for r in install_or_update(entry_for(AAA), world.workspace))
    aaa.publish("1.1.0")
    before = checkout_head(world.workspace, AAA)
    for broken in (
        {"name": AAA, "version": "1.1.0", "commit": BAD},  # not in the repository
        {"name": AAA, "version": "9.9.9", "commit": aaa.commits["1.1.0"]},  # the manifest says another version
        {"name": AAA, "version": "1.1.0", "commit": aaa.commits["1.1.0"], "manifest_sha256": "0" * 64},  # digest
        {"name": AAA, "version": "1.1.0", "commit": aaa.commits["1.1.0"], "depends_on": [SDK]},  # not the manifest's
    ):
        plan = train.plan_train(make_train([broken]), world.workspace)
        assert not plan.ok, broken
        outcome = train.apply_train(plan, world.workspace, world.entries(AAA))
        assert not outcome.ok and outcome.applied == []
        assert checkout_head(world.workspace, AAA) == before


def test_a_commit_outside_the_published_history_is_refused(world, tmp_path):
    aaa = world.make(AAA, "1.0.0")
    assert all(r.ok for r in install_or_update(entry_for(AAA), world.workspace))
    side = tmp_path / "side"
    git("clone", str(aaa.remote), str(side), cwd=tmp_path)
    git("config", "user.email", "x@example.invalid", cwd=side)
    git("config", "user.name", "X", cwd=side)
    git("checkout", "-q", "-b", "other", cwd=side)
    (side / "x.txt").write_text("x", encoding="utf-8")
    git("add", "x.txt", cwd=side)
    git("commit", "-q", "-m", "side", cwd=side)
    git("push", "-q", "origin", "other", cwd=side)  # reachable from a branch, not from main
    off_main = git("rev-parse", "HEAD", cwd=side)
    git("fetch", "-q", "origin", "other", cwd=world.workspace / AAA)  # the object is here, but not on main
    plan = train.plan_train(make_train([{"name": AAA, "version": "1.0.0", "commit": off_main}]), world.workspace)
    assert not plan.ok and "published history" in plan.problems[0]


def test_a_fresh_install_with_a_bad_commit_installs_nothing(world):
    aaa = world.make(AAA, "1.0.0")
    t = make_train([{"name": AAA, "version": "1.0.0", "commit": BAD}])
    plan = train.plan_train(t, world.workspace, fetch=None)
    assert plan.ok  # a repository that is not installed yet is checked after the clone
    outcome = train.apply_train(plan, world.workspace, world.entries(AAA))
    assert not outcome.ok
    assert not (world.workspace / AAA).exists() and not list(world.workspace.glob(".*.clone-*"))
    bad_version = make_train([{"name": AAA, "version": "7.0.0", "commit": aaa.commits["1.0.0"]}])
    outcome = train.apply_train(train.plan_train(bad_version, world.workspace, fetch=None), world.workspace, world.entries(AAA))
    assert not outcome.ok and not (world.workspace / AAA).exists()


def test_going_back_needs_the_explicit_permission(world):
    aaa = world.make(AAA, "1.0.0", "1.1.0")
    assert all(r.ok for r in install_or_update(entry_for(AAA), world.workspace))
    t = make_train([item(aaa, "1.0.0")])
    refused = train.plan_train(t, world.workspace)
    assert not refused.ok and "--allow-downgrade" in refused.problems[0]
    allowed = train.plan_train(t, world.workspace, allow_downgrade=True)
    assert allowed.ok and allowed.items[0].action == "downgrade"
    assert train.apply_train(allowed, world.workspace, world.entries(AAA)).ok
    assert checkout_head(world.workspace, AAA) == aaa.commits["1.0.0"]


def test_uncommitted_changes_block_the_repository(world):
    aaa = world.make(AAA, "1.0.0")
    assert all(r.ok for r in install_or_update(entry_for(AAA), world.workspace))
    aaa.publish("1.1.0")
    (world.workspace / AAA / "hydra-umc.project.json").write_text("{}", encoding="utf-8")
    plan = train.plan_train(make_train([item(aaa, "1.1.0")]), world.workspace)
    assert not plan.ok and "uncommitted" in plan.problems[0]


def test_the_manifest_digest_that_matches_is_accepted(world):
    aaa = world.make(AAA, "1.0.0")
    digest = hashlib.sha256((aaa.seed / "hydra-umc.project.json").read_bytes()).hexdigest()
    t = make_train([item(aaa, "1.0.0", manifest_sha256=digest)])
    outcome = train.apply_train(train.plan_train(t, world.workspace, fetch=None), world.workspace, world.entries(AAA))
    assert outcome.ok, outcome.messages


def test_a_failing_build_stops_the_train_and_rollback_restores_the_previous_state(world):
    sdk, aaa, bbb = world.make(SDK, "0.3.0"), world.make(AAA, "1.0.0"), world.make(BBB, "1.0.0")
    entries = world.entries(SDK, AAA, BBB)
    for e in entries.values():
        assert all(r.ok for r in install_or_update(e, world.workspace))
    before = {name: checkout_head(world.workspace, name) for name in (SDK, AAA, BBB)}
    sdk.publish("0.4.0")
    aaa.publish("1.1.0", depends_on=(SDK,))
    bbb.publish("1.1.0", build_ok=False, depends_on=(AAA,))
    t = make_train([item(sdk, "0.4.0"), item(aaa, "1.1.0", depends_on=[SDK]), item(bbb, "1.1.0", depends_on=[AAA])])
    plan = train.plan_train(t, world.workspace)
    assert plan.ok
    outcome = train.apply_train(plan, world.workspace, entries)
    assert not outcome.ok and outcome.failed == BBB and outcome.applied == [SDK, AAA]
    assert checkout_head(world.workspace, BBB) == before[BBB]  # the failed one was not touched
    assert checkout_head(world.workspace, SDK) == sdk.commits["0.4.0"]

    previous = train.load_previous(world.workspace)
    assert previous is not None
    back = train.plan_train(previous, world.workspace, allow_downgrade=True)
    assert back.ok and {i.name: i.action for i in back.items} == {SDK: "downgrade", AAA: "downgrade", BBB: "keep"}
    done = train.apply_train(back, world.workspace, entries, remember=False)
    assert done.ok, done.messages
    train.mark_rolled_back(world.workspace)
    assert {name: checkout_head(world.workspace, name) for name in (SDK, AAA, BBB)} == before
    assert train.load_previous(world.workspace) is None
    assert list((world.workspace / train.STATE_DIR).glob("rolled-back-*.json"))


def test_applying_a_plan_with_problems_changes_nothing(world):
    aaa = world.make(AAA, "1.0.0")
    plan = train.plan_train(make_train([item(aaa, "1.0.0", requires_min={SDK: "1.0.0"})]), world.workspace, fetch=None)
    outcome = train.apply_train(plan, world.workspace, world.entries(AAA))
    assert not outcome.ok and not (world.workspace / AAA).exists()


# ----------------------------------------------------------------------------- the command line -----------------

def run_cli(monkeypatch, capsys, world, *argv: str) -> tuple[int, str, str]:
    monkeypatch.setattr(main, "_train_entries", lambda root, names: world.entries(*names))
    parser = main.build_parser()
    args = parser.parse_args(["train", *argv, "--workspace", str(world.workspace)])
    code = args.func(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_command_line_is_a_dry_run_until_yes_and_the_switch(world, tmp_path, monkeypatch, capsys):
    aaa = world.make(AAA, "1.0.0")
    file = tmp_path / "train.json"
    file.write_text(train.train_to_json(make_train([item(aaa, "1.0.0")])), encoding="utf-8")
    monkeypatch.delenv(train.TRAINS_ENV, raising=False)

    code, out, _ = run_cli(monkeypatch, capsys, world, "plan", str(file), "--offline")
    assert code == 0 and "INSTALL" in out and not (world.workspace / AAA).exists()

    code, out, _ = run_cli(monkeypatch, capsys, world, "apply", str(file), "--offline")
    assert code == 0 and "Dry run" in out and not (world.workspace / AAA).exists()

    code, _, err = run_cli(monkeypatch, capsys, world, "apply", str(file), "--offline", "--yes")
    assert code == 1 and "switched off" in err and not (world.workspace / AAA).exists()

    monkeypatch.setenv(train.TRAINS_ENV, "1")
    code, out, _ = run_cli(monkeypatch, capsys, world, "apply", str(file), "--offline", "--yes")
    assert code == 0, out
    assert checkout_head(world.workspace, AAA) == aaa.commits["1.0.0"]


def test_the_command_line_json_and_errors(world, tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": "1.0"}', encoding="utf-8")
    code, _, err = run_cli(monkeypatch, capsys, world, "plan", str(bad))
    assert code == 1 and "ERROR" in err
    aaa = world.make(AAA, "1.0.0")
    good = tmp_path / "good.json"
    good.write_text(train.train_to_json(make_train([item(aaa, "1.0.0")])), encoding="utf-8")
    code, out, _ = run_cli(monkeypatch, capsys, world, "plan", str(good), "--offline", "--json")
    assert code == 0 and json.loads(out)["items"][0]["action"] == "install"
    code, _, err = run_cli(monkeypatch, capsys, world, "rollback", "--offline")
    assert code == 1 and "no saved previous state" in err
