# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_qt_bridge_headless.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The Qt bridge without a screen: the window must leave "busy" whatever the
background work does. Runs with the offscreen Qt platform; skipped when PySide6
is not installed (the command-line tool does not need it)."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtCore")
pytest.importorskip("PySide6.QtQml")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from hydra_umc_updater import qt_gui  # noqa: E402
from hydra_umc_updater.detect import LocalStatus  # noqa: E402
from hydra_umc_updater.install import InstallResult  # noqa: E402
from hydra_umc_updater.registry import ProjectEntry  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def _wait_until(app: QCoreApplication, condition, seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    app.processEvents()
    return condition()


def _bridge(qt_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, remote_error: Exception | None = None):
    monkeypatch.setattr(qt_gui, "_GUI_LOGGER", qt_gui.logging.getLogger("hydra_umc_updater.test"))

    def no_network(*_a, **_k):
        raise remote_error or RuntimeError("offline test")

    monkeypatch.setattr(qt_gui, "discover_remote_projects", no_network)
    monkeypatch.setattr(qt_gui, "fetch_all", lambda _entries: {})
    bridge = qt_gui.UpdaterBridge(tmp_path)
    assert _wait_until(qt_app, lambda: not bridge.busy), "the first scan never finished"
    return bridge


def _select_not_installed(bridge, tmp_path: Path) -> None:
    entry = ProjectEntry(name="HYDRA-UMC-FIXTURE", stack="python", version_file="pyproject.toml", pattern="version")
    bridge._locals = [LocalStatus(entry=entry, path=tmp_path / entry.name, installed=False, version=None)]
    bridge._selected = entry.name


def test_a_failed_github_check_leaves_the_window_free(qt_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _bridge(qt_app, tmp_path, monkeypatch, remote_error=ValueError("not what the code expects"))
    assert bridge.busy is False


def test_an_install_that_raises_leaves_the_window_free(qt_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    _select_not_installed(bridge, tmp_path)

    def exploding(*_a, **_k):
        raise OSError("the disk went away")

    monkeypatch.setattr(qt_gui, "install_or_update", exploding)
    bridge.performSelected("install", True)
    assert bridge.busy is True
    assert _wait_until(qt_app, lambda: not bridge.busy), "the window stayed busy after the install raised"


def test_an_install_that_fails_normally_leaves_the_window_free(qt_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = _bridge(qt_app, tmp_path, monkeypatch)
    _select_not_installed(bridge, tmp_path)
    monkeypatch.setattr(qt_gui, "install_or_update", lambda *_a, **_k: [InstallResult(False, "refused")])
    bridge.performSelected("install", True)
    assert _wait_until(qt_app, lambda: not bridge.busy)
