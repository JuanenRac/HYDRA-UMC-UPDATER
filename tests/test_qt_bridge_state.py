# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_qt_bridge_state.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
# ruff: noqa: F811
"""What the window reads from the Qt bridge, without a screen: the state of a row for every combination of local and remote version, the counters, the
deploy filter, the selection, the language switch and the check that refuses a second action while one runs. Offscreen Qt; skipped without PySide6."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtCore")
pytest.importorskip("PySide6.QtQml")

from test_qt_bridge_headless import _bridge, qt_app  # noqa: E402,F401  (qt_app is a fixture used by name)

from hydra_umc_updater import i18n, qt_gui, settings  # noqa: E402
from hydra_umc_updater.detect import LocalStatus  # noqa: E402
from hydra_umc_updater.github_client import RemoteStatus  # noqa: E402
from hydra_umc_updater.registry import ProjectEntry  # noqa: E402
from hydra_umc_updater.version_parse import Version  # noqa: E402


def entry(name: str, deploy: str = "cm5", family: str = "Family", parent: str | None = None) -> ProjectEntry:
    return ProjectEntry(name=name, stack="python", version_file="pyproject.toml", pattern="version", deploy=deploy, family=family, parent=parent)


def local(name: str, version: str | None, installed: bool = True, **kwargs) -> LocalStatus:
    return LocalStatus(entry=entry(name, **kwargs), path=Path("/nowhere") / name, installed=installed, version=Version.from_string(version) if version else None)


def remote(item: LocalStatus, version: str | None) -> RemoteStatus:
    return RemoteStatus(entry=item.entry, version=Version.from_string(version) if version else None, error=None if version else "down", url="u")


@pytest.mark.parametrize(
    "installed, mine, theirs, expected",
    [
        (False, None, None, "state_not_installed"),
        (True, None, "1.0.0", "state_unknown_local"),
        (True, "1.0.0", "NOREMOTE", "state_installed_not_checked"),
        (True, "1.0.0", None, "state_installed_github_unknown"),
        (True, "1.0.0", "1.0.1", "state_outdated"),
        (True, "1.0.0", "1.1.0", "state_outdated"),
        (True, "1.0.0", "2.0.0", "state_outdated"),
        (True, "1.0.1", "1.0.0", "state_ahead"),
        (True, "1.0.0", "1.0.0", "state_up_to_date"),
    ],
)
def test_the_state_of_a_row_for_every_pairing_of_versions(installed, mine, theirs, expected):
    item = local("HYDRA-UMC-A", mine, installed)
    other = None if theirs == "NOREMOTE" else remote(item, theirs)
    assert qt_gui._state_key(item, other) == expected


def test_the_counters_the_filters_and_the_selection(qt_app, tmp_path, monkeypatch):
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    a, b = local("HYDRA-UMC-A", "1.0.0"), local("HYDRA-UMC-B", "2.0.0", deploy="mobile")
    c, d = local("HYDRA-UMC-C", None, installed=False), local("HYDRA-UMC-D", "1.0.0", parent="HYDRA-UMC-A")
    bridge._locals = [a, b, c, d]
    bridge._remotes = {"HYDRA-UMC-A": remote(a, "1.2.0"), "HYDRA-UMC-B": remote(b, "2.0.0"), "HYDRA-UMC-D": remote(d, "1.0.0")}
    assert (bridge.discoveredCount, bridge.installedCount, bridge.missingCount, bridge.updateCount) == (4, 3, 1, 1)
    assert bridge.canInstallAll is True and bridge.canUpdateAll is True
    rows = {row["name"]: row for row in bridge.projects}
    assert len(rows) == 4
    assert rows["HYDRA-UMC-A"]["stateKey"] == "state_outdated" and rows["HYDRA-UMC-A"]["github"] == "1.2.0" and rows["HYDRA-UMC-A"]["local"] == "1.0.0"
    assert rows["HYDRA-UMC-C"]["local"] == "-" and rows["HYDRA-UMC-C"]["github"] == "-"
    assert rows["HYDRA-UMC-D"]["isChild"] is True and rows["HYDRA-UMC-A"]["isChild"] is False
    # the filter by deploy target
    bridge.setDeploy("mobile")
    assert [row["name"] for row in bridge.projects] == ["HYDRA-UMC-B"]
    bridge.setDeploy("not-a-target")
    assert [row["name"] for row in bridge.projects] == ["HYDRA-UMC-B"]
    bridge.setDeploy("all")
    assert len(bridge.projects) == 4
    assert [option["key"] for option in bridge.deployOptions] == list(qt_gui.DEPLOY_ORDER)
    # the selection: a name that is not there selects nothing; the buttons follow the row
    assert bridge.selectedProject == i18n.t(bridge.language, "selected_project_none")
    bridge.selectProject("HYDRA-UMC-GHOST")
    assert bridge.canInstall is False and bridge.canUpdate is False
    bridge.selectProject("HYDRA-UMC-C")
    assert bridge.selectedProject == "HYDRA-UMC-C" and bridge.canInstall is True and bridge.canUpdate is False
    bridge.selectProject("HYDRA-UMC-A")
    assert bridge.canInstall is False and bridge.canUpdate is True
    bridge.selectProject("HYDRA-UMC-B")
    assert bridge.canUpdate is False


def test_a_selected_project_with_no_version_to_compare_cannot_be_updated(qt_app, tmp_path, monkeypatch):
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    unknown, down = local("HYDRA-UMC-U", None), local("HYDRA-UMC-V", "1.0.0")
    bridge._locals = [unknown, down]
    bridge._remotes = {"HYDRA-UMC-U": remote(unknown, "9.9.9"), "HYDRA-UMC-V": remote(down, None)}
    for name in ("HYDRA-UMC-U", "HYDRA-UMC-V"):
        bridge.selectProject(name)
        assert bridge.canUpdate is False


def test_the_language_switch_accepts_only_the_languages_it_has(qt_app, tmp_path, monkeypatch):
    saved: list[str] = []
    monkeypatch.setattr(i18n, "save_lang_preference", saved.append)
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    before = bridge.language
    bridge.setLanguage("xx")
    assert bridge.language == before and saved == []
    codes = [code for code, _label in i18n.LANGUAGES]
    assert {"en", "es", "de", "fr", "it", "ja", "zh", "pt"} <= set(codes)
    for code in codes:
        bridge.setLanguage(code)
        assert bridge.language == code
        assert bridge.text("selected_project_none") == i18n.t(code, "selected_project_none")
    assert saved == codes


def test_the_operation_panel_reads_its_waiting_state_and_the_batch_heading(qt_app, tmp_path, monkeypatch):
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    assert bridge.operationVisible is False and bridge.operationProgress == 0 and bridge.operationSteps == []
    assert bridge.operationDetail == bridge.text("checkpoint_waiting")
    assert bridge.operationHeading == bridge.text("checkpoint_title")
    bridge._active_phase = "no-such-phase"
    assert bridge.operationDetail == bridge.text("checkpoint_waiting")
    bridge._operation_steps = [{"id": "build", "detail": "compiling"}]
    bridge._active_phase = "build"
    assert bridge.operationDetail == "compiling"
    bridge._batch_total, bridge._batch_current, bridge._batch_project = 3, 2, "HYDRA-UMC-B"
    heading = bridge.operationHeading
    assert "HYDRA-UMC-B" in heading and heading != bridge.text("checkpoint_title")


def test_nothing_starts_while_the_window_is_busy_and_a_missing_selection_is_said(qt_app, tmp_path, monkeypatch):
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    started: list[object] = []
    monkeypatch.setattr(qt_gui, "install_or_update", lambda *a, **k: started.append(a) or [])
    bridge._selected = ""
    bridge.performSelected("install", True)
    assert bridge.fullActivity[-1] == bridge.text("msg_select_project_first").replace("\n", " ")
    done = local("HYDRA-UMC-DONE", "1.0.0")
    todo = local("HYDRA-UMC-TODO", None, installed=False)
    bridge._locals = [done, todo]
    bridge._selected = "HYDRA-UMC-DONE"
    bridge.performSelected("install", True)
    assert bridge.fullActivity[-1] == bridge.text("msg_already_installed").format(name="HYDRA-UMC-DONE", path=done.path).replace("\n", " ")
    bridge._selected = "HYDRA-UMC-TODO"
    bridge.performSelected("update", True)
    assert bridge.fullActivity[-1] == bridge.text("msg_not_installed_yet").format(name="HYDRA-UMC-TODO").replace("\n", " ")
    bridge._busy = True
    bridge.performSelected("install", True)
    bridge.refresh(False)
    bridge.setWorkspaceUrl(str(tmp_path / "other"))
    assert started == [] and bridge.workspaceRoot == str(tmp_path)
    assert len(bridge.activity) <= 8
    assert bridge.fullActivity[-len(bridge.activity):] == bridge.activity


def test_a_new_workspace_is_remembered_and_scanned(qt_app, tmp_path, monkeypatch):
    saved: list[Path] = []
    monkeypatch.setattr(settings, "save_workspace_root", saved.append)
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    target = tmp_path / "elsewhere"
    target.mkdir()
    bridge.setWorkspaceUrl("")
    assert saved == []
    bridge.setWorkspaceUrl(str(target))
    assert saved == [target] and bridge.workspaceRoot == str(target)
    assert any(str(target) in line for line in bridge.fullActivity)


def test_the_switches_the_window_shows_are_plain_booleans(qt_app, tmp_path, monkeypatch):
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    for value in (bridge.signatureRequired, bridge.trainsEnabled, bridge.evidenceExportEnabled):
        assert isinstance(value, bool)
    assert bridge.logFilePath == ""
    assert bridge.appVersion
