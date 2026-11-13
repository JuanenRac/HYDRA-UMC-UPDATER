# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_edge_install_rollback_and_deploy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Failure paths of the promotion rollback, the fresh .venv and the deployment on the device. Nothing runs a real process: every runner is a stand-in."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hydra_umc_updater import install
from hydra_umc_updater.install import InstallResult, OsDeployOutcome, run_os_deploy


def completed(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["x"], returncode=code, stdout=out, stderr=err)


def runner_returning(code: int, out: str = "", err: str = ""):
    def run(command, **kwargs):
        run.seen = list(command)
        return completed(code, out, err)

    return run


def deploy(runner, project: str = "HYDRA-UMC-X") -> OsDeployOutcome:
    return run_os_deploy(project, runner=runner, which=lambda name: "/usr/bin/" + name, geteuid=lambda: 0)


# --------------------------------------------------------------------------- the deployment on the device


def test_the_command_is_none_without_hydra_umc_os(monkeypatch) -> None:
    monkeypatch.delenv(install.OS_DEPLOY_COMMAND_ENV, raising=False)
    assert install.os_deploy_command("P", which=lambda name: None) is None
    assert run_os_deploy("P", which=lambda name: None).status == "unavailable"


def test_sudo_is_added_only_for_a_normal_user_that_has_it(monkeypatch) -> None:
    monkeypatch.delenv(install.OS_DEPLOY_COMMAND_ENV, raising=False)
    have = lambda name: "/bin/" + name  # noqa: E731
    assert install.os_deploy_command("P", which=have, geteuid=lambda: 0) == ["hydra-umc-os", "deploy", "P", "--apply"]
    assert install.os_deploy_command("P", which=have, geteuid=lambda: 1000)[:2] == ["sudo", "-n"]
    only_os = lambda name: "/bin/x" if name == "hydra-umc-os" else None  # noqa: E731
    assert install.os_deploy_command("P", which=only_os, geteuid=lambda: 1000) == ["hydra-umc-os", "deploy", "P", "--apply"]


def test_a_custom_command_from_the_environment_is_split_and_gets_the_project(monkeypatch) -> None:
    monkeypatch.setenv(install.OS_DEPLOY_COMMAND_ENV, "ssh box  hydra-umc-os")
    assert install.os_deploy_command("P") == ["ssh", "box", "hydra-umc-os", "deploy", "P", "--apply"]


def test_every_exit_status_has_its_own_named_outcome() -> None:
    assert deploy(runner_returning(0, '{"result": "ok"}')).status == "deployed"
    assert "ok" in deploy(runner_returning(0, '{"result": "ok"}')).message
    assert deploy(runner_returning(0, "")).message.endswith("(done)")
    refused = deploy(runner_returning(2, 'noise\n{"result": "refused", "reason": "nothing here"}'))
    assert (refused.status, refused.message) == ("refused", "nothing here")
    assert deploy(runner_returning(2, '{"result": "refused"}')).message == "nothing to deploy for this project"
    assert deploy(runner_returning(2, '{"result": "other"}')).status == "failed"
    assert deploy(runner_returning(3)).status == "rolled-back"
    failed = deploy(runner_returning(1, "not json", "first\nlast line"))
    assert failed.status == "failed" and "status 1" in failed.message and "last line" in failed.message
    assert deploy(runner_returning(9, None, None)).status == "failed"


def test_a_report_line_that_is_not_an_object_is_skipped() -> None:
    outcome = deploy(runner_returning(2, '{"result": "refused", "reason": "r"}\n[1, 2]\n"text"'))
    assert outcome.status == "refused"


def test_a_runner_that_cannot_start_or_times_out_is_unavailable() -> None:
    def broken(command, **kwargs):
        raise OSError("no exec")

    def slow(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 1)

    assert deploy(broken).status == "unavailable"
    assert deploy(slow).status == "unavailable"


# --------------------------------------------------------------------------- the rollback of a promotion


def make_tree(base: Path, name: str, marker: str) -> Path:
    path = base / name
    path.mkdir()
    (path / "marker.txt").write_text(marker, encoding="utf-8")
    return path


def test_the_rollback_puts_the_previous_installation_back(tmp_path: Path) -> None:
    promoted = make_tree(tmp_path, "proj", "new")
    backup = make_tree(tmp_path, "proj.backup", "old")
    assert install._roll_back_promotion(promoted, backup) is None
    assert (promoted / "marker.txt").read_text(encoding="utf-8") == "old"
    kept = [p for p in tmp_path.iterdir() if ".unhealthy-" in p.name]
    assert len(kept) == 1 and (kept[0] / "marker.txt").read_text(encoding="utf-8") == "new"


def test_the_rollback_says_why_when_the_promoted_one_cannot_be_moved(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    backup = make_tree(tmp_path, "proj.backup", "old")
    reason = install._roll_back_promotion(missing, backup)
    assert reason and "could not move the promoted checkout aside" in reason
    assert (backup / "marker.txt").exists()


def test_the_rollback_restores_the_promoted_one_when_the_backup_is_gone(tmp_path: Path) -> None:
    promoted = make_tree(tmp_path, "proj", "new")
    reason = install._roll_back_promotion(promoted, tmp_path / "lost.backup")
    assert reason and "the promoted one was put back" in reason
    assert (promoted / "marker.txt").read_text(encoding="utf-8") == "new"


# --------------------------------------------------------------------------- the fresh .venv


def test_a_frozen_application_looks_for_python_on_the_path(monkeypatch) -> None:
    monkeypatch.setattr(install.sys, "frozen", True, raising=False)
    monkeypatch.setattr(install.shutil, "which", lambda name: "/opt/py" if name == "python" else None)
    assert install._python_for_venv() == "/opt/py"
    monkeypatch.setattr(install.shutil, "which", lambda name: None)
    assert install._python_for_venv() is None


def test_no_venv_before_means_nothing_to_recreate(tmp_path: Path) -> None:
    result = install.recreate_venv(tmp_path / "new", tmp_path / "old")
    assert result.ok and "nothing to recreate" in result.message


def test_the_venv_steps_report_their_own_failures(tmp_path: Path, monkeypatch) -> None:
    previous = tmp_path / "old"
    (previous / ".venv").mkdir(parents=True)
    checkout = tmp_path / "new"
    checkout.mkdir()
    calls: list[list[str]] = []

    def scripted(codes):
        def run(cmd, cwd, **kwargs):
            calls.append(list(cmd))
            return completed(codes[len(calls) - 1], "out\n", "")

        return run

    monkeypatch.setattr(install, "_python_for_venv", lambda: None)
    assert install.recreate_venv(checkout, previous).ok is False

    monkeypatch.setattr(install, "_python_for_venv", lambda: "python")
    monkeypatch.setattr(install, "_run", scripted([5]))
    created = install.recreate_venv(checkout, previous)
    assert created.ok is False and "exit 5" in created.message

    calls.clear()
    monkeypatch.setattr(install, "_run", scripted([0]))
    assert install.recreate_venv(checkout, previous) == InstallResult(True, "fresh .venv created", install._command_output(completed(0, "out\n", "")))

    (checkout / "requirements.txt").write_text("x\n", encoding="utf-8")
    calls.clear()
    monkeypatch.setattr(install, "_run", scripted([0, 7]))
    packages = install.recreate_venv(checkout, previous)
    assert packages.ok is False and "exit 7" in packages.message and len(calls) == 2

    calls.clear()
    monkeypatch.setattr(install, "_run", scripted([0, 0]))
    assert install.recreate_venv(checkout, previous).ok is True


@pytest.mark.parametrize("code", [124, 127])
def test_the_run_helper_turns_usual_failures_into_exit_codes(tmp_path: Path, code: int, monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        if code == 124:
            raise subprocess.TimeoutExpired(args[0], 1)
        raise FileNotFoundError("nope")

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    result = install._run(["nothing"], tmp_path, capture_output=True, timeout=1)
    assert result.returncode == code
