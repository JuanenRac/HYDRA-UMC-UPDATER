# =============================================================================
# HYDRA-UMC-UPDATER - Train rollback of first installs, `train make` and the stable plan output
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hydra_umc_updater import main, train
from hydra_umc_updater.install import install_or_update
from test_train import AAA, BBB, SDK, item, make_train, run_cli
from train_helpers import checkout_head, git


@pytest.fixture(autouse=True)
def trains_on(monkeypatch):
    monkeypatch.setenv(train.TRAINS_ENV, "1")
    monkeypatch.setenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS", "0")


def applied_world(world, tmp_path, monkeypatch, capsys, *, update_sdk: bool = True):
    """SDK installed at 0.3.0; a train moves it to 0.4.0 and clones AAA for the first time."""
    sdk = world.make(SDK, "0.3.0")
    aaa = world.make(AAA, "1.0.0")
    assert all(r.ok for r in install_or_update(world.entries(SDK)[SDK], world.workspace, build=False))
    sdk.publish("0.4.0")
    items = [item(sdk, "0.4.0"), item(aaa, "1.0.0")] if update_sdk else [item(aaa, "1.0.0")]
    file = tmp_path / "t.json"
    file.write_text(train.train_to_json(make_train(items)), encoding="utf-8")
    code, out, err = run_cli(monkeypatch, capsys, world, "apply", str(file), "--yes", "--no-build")
    assert code == 0, out + err
    return sdk, aaa


def state(world, name):
    return world.workspace / train.STATE_DIR / name


# --------------------------------------------------------------- characterization: rollback without new repos -------

def test_rollback_without_first_installs_restores_and_keeps_the_old_behaviour(world, tmp_path, monkeypatch, capsys):
    sdk = world.make(SDK, "0.3.0")
    assert all(r.ok for r in install_or_update(world.entries(SDK)[SDK], world.workspace, build=False))
    before = checkout_head(world.workspace, SDK)
    sdk.publish("0.4.0")
    file = tmp_path / "t.json"
    file.write_text(train.train_to_json(make_train([item(sdk, "0.4.0")])), encoding="utf-8")
    assert run_cli(monkeypatch, capsys, world, "apply", str(file), "--yes", "--no-build")[0] == 0
    assert json.loads(state(world, train.FIRST_INSTALLED_FILE).read_text())["repositories"] == []
    code, out, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build")
    assert code == 0, out + err
    assert checkout_head(world.workspace, SDK) == before
    assert not state(world, train.PREVIOUS_FILE).exists()
    assert (world.workspace / SDK).is_dir()


def test_remove_new_with_nothing_new_changes_nothing_extra(world, tmp_path, monkeypatch, capsys):
    sdk = world.make(SDK, "0.3.0")
    assert all(r.ok for r in install_or_update(world.entries(SDK)[SDK], world.workspace, build=False))
    sdk.publish("0.4.0")
    file = tmp_path / "t.json"
    file.write_text(train.train_to_json(make_train([item(sdk, "0.4.0")])), encoding="utf-8")
    run_cli(monkeypatch, capsys, world, "apply", str(file), "--yes", "--no-build")
    code, out, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build", "--remove-new")
    assert code == 0, out + err
    assert (world.workspace / SDK).is_dir() and not (world.workspace / train.STATE_DIR / train.TRASH_DIR).exists()


# --------------------------------------------------------------- the matrix --------------------------------------

def test_the_record_lists_only_what_the_train_cloned(world, tmp_path, monkeypatch, capsys):
    _, aaa = applied_world(world, tmp_path, monkeypatch, capsys)
    data = json.loads(state(world, train.FIRST_INSTALLED_FILE).read_text())
    assert [(r["name"], r["commit"]) for r in data["repositories"]] == [(AAA, aaa.commits["1.0.0"])]


def test_without_remove_new_a_rollback_keeps_the_new_repository(world, tmp_path, monkeypatch, capsys):
    sdk, _ = applied_world(world, tmp_path, monkeypatch, capsys)
    code, out, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build")
    assert code == 0, out + err
    assert "kept unless you add --remove-new" in out
    assert (world.workspace / AAA).is_dir()
    assert checkout_head(world.workspace, SDK) == sdk.commits["0.3.0"]
    assert state(world, train.FIRST_INSTALLED_FILE).exists()  # still there: it can be removed later


def test_remove_new_without_yes_is_a_dry_run(world, tmp_path, monkeypatch, capsys):
    sdk, _ = applied_world(world, tmp_path, monkeypatch, capsys)
    code, out, _ = run_cli(monkeypatch, capsys, world, "rollback", "--remove-new")
    assert code == 0 and "REMOVE" in out and "Dry run" in out
    assert (world.workspace / AAA).is_dir()
    assert checkout_head(world.workspace, SDK) == sdk.commits["0.4.0"]


def test_remove_new_with_yes_moves_the_new_repository_to_the_trash_and_restores_the_rest(world, tmp_path, monkeypatch, capsys):
    sdk, aaa = applied_world(world, tmp_path, monkeypatch, capsys)
    code, out, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build", "--remove-new")
    assert code == 0, out + err
    assert not (world.workspace / AAA).exists()
    kept = list((world.workspace / train.STATE_DIR / train.TRASH_DIR).glob(f"{AAA}.removed-*"))
    assert len(kept) == 1 and (kept[0] / ".git").is_dir()  # moved, not deleted
    assert git("rev-parse", "HEAD", cwd=kept[0]) == aaa.commits["1.0.0"]
    assert checkout_head(world.workspace, SDK) == sdk.commits["0.3.0"]  # an existing repository is only rolled back
    assert not state(world, train.FIRST_INSTALLED_FILE).exists()
    assert list((world.workspace / train.STATE_DIR).glob("rolled-back-first-installed-*.json"))


def test_a_new_repository_with_a_modified_tracked_file_is_never_removed(world, tmp_path, monkeypatch, capsys):
    sdk, _ = applied_world(world, tmp_path, monkeypatch, capsys)
    (world.workspace / AAA / "hydra-umc.project.json").write_text("{}", encoding="utf-8")
    code, _, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build", "--remove-new")
    assert code == 1 and AAA in err
    assert (world.workspace / AAA).is_dir()
    assert checkout_head(world.workspace, SDK) == sdk.commits["0.4.0"]  # all or nothing: nothing was restored either
    assert state(world, train.PREVIOUS_FILE).exists()


def test_a_new_repository_with_an_untracked_file_is_never_removed(world, tmp_path, monkeypatch, capsys):
    applied_world(world, tmp_path, monkeypatch, capsys)
    (world.workspace / AAA / "my-notes.txt").write_text("keep me", encoding="utf-8")
    code, _, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build", "--remove-new")
    assert code == 1 and AAA in err
    assert (world.workspace / AAA / "my-notes.txt").read_text() == "keep me"


def test_a_new_repository_that_moved_on_is_never_removed(world, tmp_path, monkeypatch, capsys):
    _, aaa = applied_world(world, tmp_path, monkeypatch, capsys)
    git("config", "user.email", "t@example.invalid", cwd=world.workspace / AAA)
    git("config", "user.name", "T", cwd=world.workspace / AAA)
    git("commit", "--allow-empty", "-m", "my own work", cwd=world.workspace / AAA)
    code, out, err = run_cli(monkeypatch, capsys, world, "rollback", "--remove-new")
    assert code == 1 and "BLOCKED" in out
    assert (world.workspace / AAA).is_dir()


def test_with_the_trains_switched_off_nothing_is_removed(world, tmp_path, monkeypatch, capsys):
    applied_world(world, tmp_path, monkeypatch, capsys)
    monkeypatch.setenv(train.TRAINS_ENV, "0")
    code, _, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--remove-new")
    assert code == 1 and "switched off" in err
    assert (world.workspace / AAA).is_dir()


def test_a_train_that_only_cloned_new_repositories_can_be_rolled_back(world, tmp_path, monkeypatch, capsys):
    applied_world(world, tmp_path, monkeypatch, capsys, update_sdk=False)
    assert not state(world, train.PREVIOUS_FILE).exists()  # nothing was installed before
    code, out, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build", "--remove-new")
    assert code == 0, out + err
    assert not (world.workspace / AAA).exists()


def test_a_damaged_record_stops_a_removal_but_not_a_plain_rollback(world, tmp_path, monkeypatch, capsys):
    sdk, _ = applied_world(world, tmp_path, monkeypatch, capsys)
    state(world, train.FIRST_INSTALLED_FILE).write_text("not json", encoding="utf-8")
    code, _, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--remove-new")
    assert code == 1 and "damaged" in err and (world.workspace / AAA).is_dir()
    code, _, err = run_cli(monkeypatch, capsys, world, "rollback", "--yes", "--no-build")
    assert code == 0 and "WARNING" in err
    assert checkout_head(world.workspace, SDK) == sdk.commits["0.3.0"]


@pytest.mark.parametrize("bad", ["../escape", "HYDRA-UMC-X/../../y", "evil", ""])
def test_a_record_naming_something_outside_the_family_is_blocked(world, bad):
    (world.workspace / train.STATE_DIR).mkdir()
    record = {"schema_version": "1.0", "train": "t", "repositories": [{"name": bad, "commit": "a" * 40}]}
    state(world, train.FIRST_INSTALLED_FILE).write_text(json.dumps(record), encoding="utf-8")
    assert [r.action for r in train.plan_removals(world.workspace)] == ["blocked"]
    ok, _ = train.remove_first_installed(world.workspace)
    assert not ok


def test_a_new_repository_that_is_already_gone_is_not_an_error(world):
    (world.workspace / train.STATE_DIR).mkdir()
    record = {"schema_version": "1.0", "train": "t", "repositories": [{"name": AAA, "commit": "a" * 40}]}
    state(world, train.FIRST_INSTALLED_FILE).write_text(json.dumps(record), encoding="utf-8")
    assert [r.action for r in train.plan_removals(world.workspace)] == ["gone"]
    assert train.remove_first_installed(world.workspace) == (True, [])


def test_the_folder_must_be_a_real_checkout_inside_the_workspace(world, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / ".git").mkdir()
    link = world.workspace / AAA
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links need a privilege on this machine")
    (world.workspace / train.STATE_DIR).mkdir()
    record = {"schema_version": "1.0", "train": "t", "repositories": [{"name": AAA, "commit": "a" * 40}]}
    state(world, train.FIRST_INSTALLED_FILE).write_text(json.dumps(record), encoding="utf-8")
    assert [r.action for r in train.plan_removals(world.workspace)] == ["blocked"]
    assert outside.is_dir()


def test_rollback_json_lists_the_removals(world, tmp_path, monkeypatch, capsys):
    applied_world(world, tmp_path, monkeypatch, capsys)
    code, out, _ = run_cli(monkeypatch, capsys, world, "rollback", "--json", "--remove-new")
    data = json.loads(out)
    assert code == 0 and data["remove_new"] is True
    assert [(r["name"], r["action"]) for r in data["removals"]] == [(AAA, "remove")]


# --------------------------------------------------------------- the stable output of `train plan --json` ----------

def test_plan_json_has_a_documented_stable_shape(world, tmp_path, monkeypatch, capsys):
    aaa = world.make(AAA, "1.0.0")
    file = tmp_path / "t.json"
    file.write_text(train.train_to_json(make_train([item(aaa, "1.0.0")])), encoding="utf-8")
    code, out, _ = run_cli(monkeypatch, capsys, world, "plan", str(file), "--json")
    data = json.loads(out)
    assert code == 0
    assert set(data) == {"schema_version", "train", "ok", "problems", "items"}
    assert data["schema_version"] == "1.0" and data["ok"] is True and data["problems"] == []
    assert set(data["items"][0]) == {"name", "action", "version", "commit", "installed_version", "installed_commit", "reason"}
    assert data["items"][0]["action"] in {"install", "update", "downgrade", "keep", "blocked"}


# --------------------------------------------------------------- train make --------------------------------------

GENERATOR_SOURCE = Path(__file__).resolve().parents[2] / "HYDRA-UMC-SDK" / "tools" / "ecosystem_release.py"


def install_real_generator(world):
    if not GENERATOR_SOURCE.is_file():
        pytest.skip("the SDK checkout is not next to this one")
    target = world.workspace / train.GENERATOR
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(GENERATOR_SOURCE, target)


def test_make_uses_the_sdk_generator_and_writes_a_train_the_updater_reads(world, tmp_path, monkeypatch, capsys):
    world.make(SDK, "0.3.0")
    world.make(AAA, "1.0.0")
    world.make(BBB, "2.0.0")
    for name in (SDK, AAA, BBB):
        assert all(r.ok for r in install_or_update(world.entries(name)[name], world.workspace, build=False))
    install_real_generator(world)
    out_file = tmp_path / "made.json"
    code, out, err = run_cli_make(monkeypatch, capsys, world, "--out", str(out_file), "--name", "made")
    assert code == 0, out + err
    loaded = train.load_train(out_file)  # parses with the digest check
    assert loaded.name == "made" and loaded.digest and [r.name for r in loaded.repos] == [AAA, BBB, SDK]
    for repo in loaded.repos:
        assert repo.commit == checkout_head(world.workspace, repo.name)
    code, out, _ = run_cli(monkeypatch, capsys, world, "plan", str(out_file), "--json")
    assert code == 0 and {i["action"] for i in json.loads(out)["items"]} == {"keep"}


def run_cli_make(monkeypatch, capsys, world, *argv: str):
    args = main.build_parser().parse_args(["train", "make", *argv, "--workspace", str(world.workspace)])
    code = args.func(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_make_refuses_without_the_generator_and_never_overwrites(world, tmp_path, monkeypatch, capsys):
    out_file = tmp_path / "t.json"
    code, _, err = run_cli_make(monkeypatch, capsys, world, "--out", str(out_file))
    assert code == 1 and "generator was not found" in err and not out_file.exists()
    out_file.write_text("mine", encoding="utf-8")
    code, _, err = run_cli_make(monkeypatch, capsys, world, "--out", str(out_file))
    assert code == 1 and "already exists" in err and out_file.read_text() == "mine"


def test_make_from_a_release_file_and_failures_are_closed(world, tmp_path, monkeypatch, capsys):
    release = tmp_path / "release.json"
    release.write_text(json.dumps({"schema_version": "1.0", "ecosystem": "HYDRA-UMC",
                                   "repositories": [{"name": AAA, "version": "1.0.0", "commit": "a" * 40}]}), encoding="utf-8")
    out_file = tmp_path / "t.json"
    code, _, err = run_cli_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release))
    assert code == 0, err
    assert train.load_train(out_file).repos[0].commit == "a" * 40
    for broken in ("not json", "{}", json.dumps({"repositories": [{"name": AAA}]}),
                   json.dumps({"repositories": [{"name": "evil", "version": "1.0.0", "commit": "a" * 40}]})):
        release.write_text(broken, encoding="utf-8")
        code, _, err = run_cli_make(monkeypatch, capsys, world, "--out", str(tmp_path / "x.json"), "--from-release", str(release))
        assert code == 1 and "ERROR" in err and not (tmp_path / "x.json").exists()


def test_make_with_a_failing_generator_writes_nothing(world, tmp_path, monkeypatch, capsys):
    generator = world.workspace / train.GENERATOR
    generator.parent.mkdir(parents=True)
    generator.write_text("import sys\nprint('boom', file=sys.stderr)\nsys.exit(1)\n", encoding="utf-8")
    out_file = tmp_path / "t.json"
    code, _, err = run_cli_make(monkeypatch, capsys, world, "--out", str(out_file))
    assert code == 1 and "boom" in err and not out_file.exists()


def test_make_tells_how_to_sign_when_a_signature_is_required(world, tmp_path, monkeypatch, capsys):
    release = tmp_path / "release.json"
    release.write_text(json.dumps({"repositories": [{"name": AAA, "version": "1.0.0", "commit": "a" * 40}]}), encoding="utf-8")
    monkeypatch.setenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS", "1")
    code, out, _ = run_cli_make(monkeypatch, capsys, world, "--out", str(tmp_path / "t.json"), "--from-release", str(release))
    assert code == 0 and "train sign" in out
