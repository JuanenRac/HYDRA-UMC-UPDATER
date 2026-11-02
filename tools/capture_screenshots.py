# =============================================================================
# HYDRA-UMC-UPDATER - tools/capture_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Takes the screenshots of the README: the real Qt Quick window, without a window on the desktop (the offscreen Qt platform and the software renderer),
# with a made-up list of projects and versions instead of the ones the program finds on disk and on GitHub. Nothing real is behind the pictures and
# nothing is sent to any network or written to the settings of the user.
#
#   python tools/capture_screenshots.py              writes images/screenshots/<name>.png at 1920x1080
#   python tools/capture_screenshots.py --out DIR    writes them in DIR instead, to look at them before they replace the ones in the repository
#
# It takes no mouse or keyboard of the desktop. Run it from the repository root, with the interpreter of the project (the one that has PySide6).
# =============================================================================
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))   # the offscreen platform finds no fonts by itself
WORKSPACE = Path("C:/hydra-bench/workspace")   # only shown in the window: nothing is read from or written to it
HERE =Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication, QWindow  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401  (so that the window comes back as a Quick window, which can grab itself)

from hydra_umc_updater import qt_gui  # noqa: E402
from hydra_umc_updater.detect import LocalStatus  # noqa: E402
from hydra_umc_updater.github_client import RemoteStatus  # noqa: E402
from hydra_umc_updater.registry import ProjectEntry  # noqa: E402
from hydra_umc_updater.version_parse import Version  # noqa: E402

# (name, family, role, stack, deploy, maturity, installed version, version on GitHub, notes)
PROJECTS = [
    ("HYDRA-UMC-SERVER", "HYDRA-UMC", "service", "Node.js", "cm5", "established", "0.8.0.3", "0.8.0.3", "Sample server of the bench."),
    ("HYDRA-UMC-STUDIO", "HYDRA-UMC", "ui", "TypeScript", "cm5", "established", "0.8.0.1", "0.8.0.3", "Sample web interface of the bench."),
    ("HYDRA-UMC-DATALAKE", "HYDRA-UMC", "service", "Python", "cm5", "functional", "0.8.0.2", "0.8.0.2", "Sample time-series store."),
    ("HYDRA-UMC-MQTT-BROKER", "HYDRA-UMC", "service", "Node.js", "cm5", "functional", "0.8.0.3", "0.8.0.3", "Sample message broker."),
    ("HYDRA-UMC-VOICE-UI", "HYDRA-UMC", "ui", "Python", "cm5", "functional", "0.8.0.0", "0.8.0.2", "Sample voice interface."),
    ("HYDRA-UMC-SDK", "HYDRA-UMC", "library", "Python", "cm5", "established", "0.3.6", "0.3.6", "Sample shared library."),
    ("HYDRA-UMC-UPDATER", "HYDRA-UMC", "tool", "Python", "cm5", "functional", "", "0.8.0.3", "Sample updater (not installed on the bench)."),
    ("HYDRA-UMC-ANDROID-CONTROL", "HYDRA-UMC", "ui", "Kotlin", "mobile", "functional", "0.8.0.2", "0.8.0.3", "Sample mobile app."),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(HERE / "images" / "screenshots"))
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    qt_gui.UpdaterBridge.refresh = lambda self, offline=False: None   # no scan of the disk and no call to GitHub
    qt_gui.UpdaterBridge.setLanguage = lambda self, language: None    # the preference of the user is not written
    bridge = qt_gui.UpdaterBridge(WORKSPACE)
    bridge._lang = "en"
    locals_, remotes = [], {}
    for name, family, role, stack, deploy, maturity, installed, remote, notes in PROJECTS:
        entry = ProjectEntry(name=name, stack=stack, version_file="VERSION", pattern=r"(\d+\.\d+\.\d+(?:\.\d+)?)", deploy=deploy, maturity=maturity, role=role,
                             family=family, notes=notes, tech=(stack,), note="Sample build note.")
        locals_.append(LocalStatus(entry=entry, path=WORKSPACE / name, installed=bool(installed), version=Version.from_string(installed) if installed else None))
        remotes[name] = RemoteStatus(entry=entry, version=Version.from_string(remote))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", bridge)
    engine.load(QUrl.fromLocalFile(str(HERE / "src" / "hydra_umc_updater" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("SCREENSHOTS=FAIL the window did not load")
        return 1
    root = engine.rootObjects()[0]
    root.setVisibility(QWindow.Visibility.Windowed)   # the window opens maximized: here it gets the size of the pictures instead
    root.resize(1920, 1080)
    root.show()
    bridge._on_remote_result(locals_, remotes, ())
    bridge._activity.clear()
    bridge._append_activity("Sample bench: the list of projects is made up.")
    bridge.selectProject("HYDRA-UMC-STUDIO")
    for _ in range(30):
        app.processEvents()
    path = out / "overview.png"
    image = root.grabWindow()
    image.save(str(path))
    print("wrote", path, image.width(), "x", image.height())
    return 0


if __name__ == "__main__":
    sys.exit(main())
