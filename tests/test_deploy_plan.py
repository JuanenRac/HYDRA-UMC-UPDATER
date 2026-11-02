# =============================================================================
# HYDRA-UMC-UPDATER - deployment plan and common core tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_umc_updater import deploy_plan, install, main, updater_core
from hydra_umc_updater.evidence import read_attempts


def _manifest(name: str, version: str, *, target: str = "cm5", depends: list[str] | None = None) -> str:
    data = {
        "schema_version": "1.0",
        "ecosystem": "HYDRA-UMC",
        "name": name,
        "version": version,
        "role": "service",
        "stack": "python",
        "technologies": ["python"],
        "deployment_target": target,
        "maturity": "functional",
        "family": "test",
        "parent": None,
        "native_version": {"file": "VERSION", "pattern": r"^(\d+)\.(\d+)\.(\d+)$"},
        "build": "build-test.sh",
        "notes": "test",
    }
    if depends:
        data["depends_on"] = depends
    return json.dumps(data)


def _row(source: str, target: str, *, contract: int | None = 1, exempt: str | None = None) -> dict:
    return {"script": f"install_{source.lower()}.sh", "source": source, "target": target, "unit": f"{source.lower()}.service", "contract": contract, "deploy_exempt": exempt}


@pytest.fixture
def scene(tmp_path: Path):
    """A workspace with five projects and a device tree, and the table of installers that joins them."""
    workspace = tmp_path / "ws"
    device = tmp_path / "opt"
    (workspace / "HYDRA-UMC-OS" / "provisioning").mkdir(parents=True)
    projects = {
        # name: (checkout version, device version or None, target, depends)
        "HYDRA-UMC-A": ("0.2.0", "0.1.0", "cm5", []),
        "HYDRA-UMC-B": ("0.3.0", "0.3.0", "cm5", ["HYDRA-UMC-A"]),
        "HYDRA-UMC-C": ("0.1.0", "0.2.0", "cm5", []),
        "HYDRA-UMC-D": ("1.0.0", None, "cm5", []),
        "HYDRA-UMC-E": ("1.0.0", None, "user-pc", []),
    }
    rows = []
    for name, (checkout, running, target, depends) in projects.items():
        (workspace / name).mkdir()
        (workspace / name / "hydra-umc.project.json").write_text(_manifest(name, checkout, target=target, depends=depends), encoding="utf-8")
        path = f"/opt/hydra-umc/{name.lower()}"
        rows.append(_row(name, path))
        if running:
            installed = device / name.lower()
            installed.mkdir(parents=True)
            (installed / "hydra-umc.project.json").write_text(_manifest(name, running, target=target), encoding="utf-8")
    rows.append(_row("HYDRA-UMC-F", "/opt/hydra-umc/f"))  # not checked out
    rows.append({"script": "install_cm5_base.sh", "source": None, "target": None, "contract": None})
    table = {"format": "hydra-install-plan/2", "supported_contract": 1, "installers": rows}
    (workspace / "HYDRA-UMC-OS" / "provisioning" / "install_plan.json").write_text(json.dumps(table), encoding="utf-8")
    return workspace, device


def _plan(scene, **kwargs):
    workspace, device = scene
    return deploy_plan.build_plan(workspace, root=str(device), command_for=lambda project: ["hydra-umc-os", "deploy", project, "--apply"], **kwargs)


def test_the_plan_compares_the_checkout_with_what_the_device_runs(scene) -> None:
    states = {row.project: row.state for row in _plan(scene).rows}
    assert states == {
        "HYDRA-UMC-A": deploy_plan.DEPLOY,
        "HYDRA-UMC-B": deploy_plan.CURRENT,
        "HYDRA-UMC-C": deploy_plan.AHEAD,
        "HYDRA-UMC-D": deploy_plan.NOT_INSTALLED,
        "HYDRA-UMC-E": deploy_plan.NOT_CM5,
        "HYDRA-UMC-F": deploy_plan.NO_CHECKOUT,
    }
    (step,) = _plan(scene).steps
    assert step.project == "HYDRA-UMC-A" and step.device_version == "0.1.0" and step.checkout_version == "0.2.0"
    assert step.command == ("hydra-umc-os", "deploy", "HYDRA-UMC-A", "--apply")


def test_a_first_installation_is_never_a_step_of_the_plan(scene) -> None:
    assert all(row.project != "HYDRA-UMC-D" for row in _plan(scene).steps)


def test_the_steps_follow_depends_on(scene) -> None:
    workspace, device = scene
    # B is now behind and depends on A, which is behind too
    (device / "hydra-umc-b" / "hydra-umc.project.json").write_text(_manifest("HYDRA-UMC-B", "0.2.0"), encoding="utf-8")
    names = [row.project for row in _plan(scene).steps]
    assert names == ["HYDRA-UMC-A", "HYDRA-UMC-B"]


def test_an_installer_outside_the_contract_is_reported_as_manual(scene) -> None:
    workspace, device = scene
    path = workspace / "HYDRA-UMC-OS" / "provisioning" / "install_plan.json"
    table = json.loads(path.read_text(encoding="utf-8"))
    table["installers"][0]["contract"] = None
    table["installers"][0]["deploy_exempt"] = "it builds on the device"
    path.write_text(json.dumps(table), encoding="utf-8")
    row = next(item for item in _plan(scene).rows if item.project == "HYDRA-UMC-A")
    assert row.state == deploy_plan.MANUAL and "builds on the device" in row.note and not _plan(scene).steps


def test_the_plan_changes_nothing_in_the_workspace_or_the_device(scene) -> None:
    workspace, device = scene
    before = sorted(str(p.relative_to(device.parent)) for p in device.parent.rglob("*"))
    _plan(scene)
    assert sorted(str(p.relative_to(device.parent)) for p in device.parent.rglob("*")) == before


def test_a_table_that_cannot_be_read_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(deploy_plan.PlanError):
        deploy_plan.build_plan(tmp_path)
    broken = tmp_path / "plan.json"
    broken.write_text(json.dumps({"format": "other", "installers": []}), encoding="utf-8")
    with pytest.raises(deploy_plan.PlanError):
        deploy_plan.load_install_plan(broken)


def test_the_installed_path_is_remapped_below_the_given_root() -> None:
    assert deploy_plan._remap("/opt/hydra-umc/server", "/mnt/image/opt/hydra-umc") == "/mnt/image/opt/hydra-umc/server"
    assert deploy_plan._remap("/opt/hydra-umc/server", "/opt/hydra-umc") == "/opt/hydra-umc/server"
    assert deploy_plan._remap("/etc/other", "/mnt/x") == "/etc/other"


def test_applying_needs_the_confirmation_and_the_switch(scene, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace, _ = scene
    calls: list[str] = []

    def fake(project: str) -> install.OsDeployOutcome:
        calls.append(project)
        return install.OsDeployOutcome("deployed", "ok")

    plan = _plan(scene)
    monkeypatch.delenv(install.OS_DEPLOY_ENV, raising=False)
    assert deploy_plan.apply_plan(plan, workspace, confirmed=False, deploy=fake).ok is False
    off = deploy_plan.apply_plan(plan, workspace, confirmed=True, deploy=fake)
    assert off.ok is False and "switched off" in off.messages[0] and calls == []
    monkeypatch.setenv(install.OS_DEPLOY_ENV, "1")
    done = deploy_plan.apply_plan(plan, workspace, confirmed=True, deploy=fake)
    assert done.ok and calls == ["HYDRA-UMC-A"]
    (attempt,) = read_attempts(workspace)
    assert attempt["project"] == "HYDRA-UMC-A" and attempt["ok"] is True and attempt["versionBefore"] == "0.1.0"


def test_a_bad_signature_stops_before_anything_is_deployed(scene, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace, _ = scene
    monkeypatch.setenv(install.OS_DEPLOY_ENV, "1")
    monkeypatch.setenv(install.REQUIRE_SIGNED_ENV, "1")
    calls: list[str] = []
    outcome = deploy_plan.apply_plan(
        _plan(scene),
        workspace,
        confirmed=True,
        deploy=lambda project: calls.append(project) or install.OsDeployOutcome("deployed", "ok"),
        verify_signature=lambda path: (False, "no signature"),
    )
    assert outcome.ok is False and calls == [] and "signature" in outcome.messages[-1]
    assert read_attempts(workspace)[0]["ok"] is False


def test_the_first_failed_step_stops_the_rest(scene, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace, device = scene
    (device / "hydra-umc-b" / "hydra-umc.project.json").write_text(_manifest("HYDRA-UMC-B", "0.2.0"), encoding="utf-8")
    monkeypatch.setenv(install.OS_DEPLOY_ENV, "1")
    calls: list[str] = []

    def failing(project: str) -> install.OsDeployOutcome:
        calls.append(project)
        return install.OsDeployOutcome("rolled-back", "the unit did not hold")

    outcome = deploy_plan.apply_plan(_plan(scene), workspace, confirmed=True, deploy=failing)
    assert outcome.ok is False and calls == ["HYDRA-UMC-A"] and "were not deployed" in outcome.messages[-1]


def test_the_command_prints_the_plan_as_json_and_changes_nothing(scene, capsys: pytest.CaptureFixture[str]) -> None:
    workspace, device = scene
    args = main.build_parser().parse_args(["deploy-plan", "--workspace", str(workspace), "--device-root", str(device), "--json"])
    assert args.func(args) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema_version"] == "1.0" and data["steps"] == 1


def test_the_command_reports_an_unreadable_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = main.build_parser().parse_args(["deploy-plan", "--workspace", str(tmp_path)])
    assert args.func(args) == 1 and "ERROR" in capsys.readouterr().err


def test_the_profile_builds_its_own_names_and_refuses_an_unknown_family(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = updater_core.HYDRA_PROFILE
    assert profile.env_name("OS_DEPLOY") == "HYDRA_UMC_UPDATER_OS_DEPLOY"
    monkeypatch.setenv("HYDRA_UMC_UPDATER_X", "yes")
    assert profile.env_flag("X") is True
    monkeypatch.setenv("HYDRA_UMC_UPDATER_X", "off")
    assert profile.env_flag("X") is False
    monkeypatch.setenv("HYDRA_UMC_UPDATER_X", "maybe")
    assert profile.env_flag("X") is None
    assert updater_core.profile_for("HYDRA-UMC") is profile
    with pytest.raises(KeyError):
        updater_core.profile_for("URTC")


def test_the_core_modules_named_exist() -> None:
    import importlib

    for name in updater_core.CORE_MODULES:
        importlib.import_module(f"hydra_umc_updater.{name}")
