# =============================================================================
# HYDRA-UMC-UPDATER - `train make` fills in manifest_sha256 and depends_on from the manifests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from hydra_umc_updater import main, train
from hydra_umc_updater.install import install_or_update
from test_train import AAA, BBB, SDK, run_cli


@pytest.fixture(autouse=True)
def trains_on(monkeypatch):
    monkeypatch.setenv(train.TRAINS_ENV, "1")
    monkeypatch.setenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS", "0")


def run_make(monkeypatch, capsys, world, *argv: str):
    args = main.build_parser().parse_args(["train", "make", *argv, "--workspace", str(world.workspace)])
    code = args.func(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def release_file(tmp_path: Path, *items: tuple[str, str, str]) -> Path:
    path = tmp_path / "release.json"
    path.write_text(
        json.dumps({"schema_version": "1.0", "ecosystem": "HYDRA-UMC",
                    "repositories": [{"name": n, "version": v, "commit": c} for n, v, c in items]}),
        encoding="utf-8",
    )
    return path


def install(world, *names: str) -> None:
    for name in names:
        assert all(r.ok for r in install_or_update(world.entries(name)[name], world.workspace, build=False))


def manifest_digest(world, name: str, commit: str) -> str:
    shown = subprocess.run(["git", "show", f"{commit}:hydra-umc.project.json"], cwd=world.workspace / name, check=True, capture_output=True)
    return hashlib.sha256(shown.stdout).hexdigest()


def repositories(out_file: Path) -> dict[str, dict]:
    return {r["name"]: r for r in json.loads(out_file.read_text(encoding="utf-8"))["repositories"]}


def test_make_fills_the_manifest_digest_and_the_dependencies_from_the_checkouts(world, tmp_path, monkeypatch, capsys):
    sdk = world.make(SDK, "0.3.0")
    aaa = world.make(AAA, "1.0.0", depends_on=(SDK,))
    install(world, SDK, AAA)
    out_file = tmp_path / "t.json"
    release = release_file(tmp_path, (SDK, "0.3.0", sdk.commits["0.3.0"]), (AAA, "1.0.0", aaa.commits["1.0.0"]))
    code, out, err = run_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release))
    assert code == 0, out + err
    assert "NOTE" not in err
    by_name = repositories(out_file)
    assert by_name[SDK]["depends_on"] == []
    assert by_name[AAA]["depends_on"] == [SDK]
    assert by_name[SDK]["manifest_sha256"] == manifest_digest(world, SDK, sdk.commits["0.3.0"])
    assert by_name[AAA]["manifest_sha256"] == manifest_digest(world, AAA, aaa.commits["1.0.0"])
    # what was written is what the updater reads, and the plan against the same checkouts agrees with every field
    loaded = train.load_train(out_file)
    assert loaded.by_name()[AAA].depends_on == (SDK,)
    code, out, _ = run_cli(monkeypatch, capsys, world, "plan", str(out_file), "--json")
    assert code == 0 and {i["action"] for i in json.loads(out)["items"]} == {"keep"}


def test_a_repository_that_is_not_checked_out_is_left_out_with_a_note_or_refused(world, tmp_path, monkeypatch, capsys):
    release = release_file(tmp_path, (AAA, "1.0.0", "a" * 40))
    out_file = tmp_path / "t.json"
    code, _, err = run_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release))
    assert code == 0 and f"NOTE: {AAA}: not checked out" in err
    assert "manifest_sha256" not in repositories(out_file)[AAA] and "depends_on" not in repositories(out_file)[AAA]
    strict = tmp_path / "strict.json"
    code, _, err = run_make(monkeypatch, capsys, world, "--out", str(strict), "--from-release", str(release), "--require-manifests")
    assert code == 1 and "not checked out" in err and not strict.exists()


def test_a_wrong_version_or_unknown_commit_writes_nothing(world, tmp_path, monkeypatch, capsys):
    aaa = world.make(AAA, "1.0.0")
    install(world, AAA)
    for item, expected in (
        ((AAA, "9.9.9", aaa.commits["1.0.0"]), "9.9.9"),
        ((AAA, "1.0.0", "b" * 40), "not in the repository"),
    ):
        out_file = tmp_path / "t.json"
        code, _, err = run_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release_file(tmp_path, item)))
        assert code == 1 and expected in err and not out_file.exists()


def test_a_dependency_that_is_neither_in_the_train_nor_installed_writes_nothing(world, tmp_path, monkeypatch, capsys):
    world.make(SDK, "0.3.0")
    aaa = world.make(AAA, "1.0.0", depends_on=(SDK,))
    install(world, AAA)  # the SDK is not checked out
    out_file = tmp_path / "t.json"
    code, _, err = run_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release_file(tmp_path, (AAA, "1.0.0", aaa.commits["1.0.0"]))))
    assert code == 1 and "neither in the train nor installed" in err and not out_file.exists()


def test_a_dependency_cycle_writes_nothing(world, tmp_path, monkeypatch, capsys):
    aaa = world.make(AAA, "1.0.0", depends_on=(BBB,))
    bbb = world.make(BBB, "1.0.0", depends_on=(AAA,))
    install(world, AAA, BBB)
    out_file = tmp_path / "t.json"
    release = release_file(tmp_path, (AAA, "1.0.0", aaa.commits["1.0.0"]), (BBB, "1.0.0", bbb.commits["1.0.0"]))
    code, _, err = run_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release))
    assert code == 1 and "cycle" in err and not out_file.exists()


def test_no_manifest_fill_writes_only_name_version_and_commit(world, tmp_path, monkeypatch, capsys):
    sdk = world.make(SDK, "0.3.0")
    install(world, SDK)
    out_file = tmp_path / "t.json"
    release = release_file(tmp_path, (SDK, "0.3.0", sdk.commits["0.3.0"]))
    code, _, err = run_make(monkeypatch, capsys, world, "--out", str(out_file), "--from-release", str(release), "--no-manifest-fill")
    assert code == 0 and "NOTE" not in err
    assert set(repositories(out_file)[SDK]) == {"name", "version", "commit"}


def test_make_with_the_real_generator_fills_the_fields_too(world, tmp_path, monkeypatch, capsys):
    from test_train_rollback_new import install_real_generator

    sdk = world.make(SDK, "0.3.0")
    aaa = world.make(AAA, "1.0.0", depends_on=(SDK,))
    install(world, SDK, AAA)
    install_real_generator(world)
    out_file = tmp_path / "made.json"
    code, out, err = run_make(monkeypatch, capsys, world, "--out", str(out_file))
    assert code == 0, out + err
    by_name = repositories(out_file)
    assert by_name[AAA]["depends_on"] == [SDK]
    assert by_name[SDK]["manifest_sha256"] == manifest_digest(world, SDK, sdk.commits["0.3.0"])
    assert aaa.commits["1.0.0"] == by_name[AAA]["commit"]
