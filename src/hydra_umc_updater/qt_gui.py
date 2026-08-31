# =============================================================================
# HYDRA-UMC-UPDATER - Qt Quick / QML GUI bridge: qt_gui.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The visual QML shell over the updater's existing, conservative core.

This module deliberately contains no alternative update implementation.  QML
calls this bridge; the bridge calls the same discover_workspace(), GitHub
discovery and install_or_update() functions used by the CLI.  That keeps the
new game-like desktop presentation honest: it is visualising the real updater,
not a separate demo whose data can drift away from the command-line tool.

PySide6 is imported only when the desktop GUI is launched.  The CLI remains
stdlib-only and continues to work on a headless CM5 without Qt installed.
"""
from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from . import __version__, i18n
from .detect import LocalStatus, discover_workspace
from .github_client import RemoteStatus, discover_remote_projects, fetch_all
from .install import install_or_update
from .registry import GITHUB_OWNER


DEPLOY_ORDER = ("all", "cm5", "user-pc", "mobile", "wearable")


def _state_key(local: LocalStatus, remote: RemoteStatus | None) -> str:
    if not local.installed:
        return "state_not_installed"
    if local.version is None:
        return "state_unknown_local"
    if remote is None:
        return "state_installed_not_checked"
    if remote.version is None:
        return "state_installed_github_unknown"
    if local.version < remote.version:
        return "state_outdated"
    if remote.version < local.version:
        return "state_ahead"
    return "state_up_to_date"


class UpdaterBridge(QObject):
    """A small QML-facing state model over the actual updater services."""

    projectsChanged = Signal()
    selectionChanged = Signal()
    summaryChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    activityChanged = Signal()
    operationChanged = Signal()
    languageChanged = Signal()
    deployOptionsChanged = Signal()
    _remoteResult = Signal(object, object, object)
    _actionResult = Signal(str, object)
    _operationCheckpoint = Signal(str, str)
    _batchProject = Signal(int, int, str)

    def __init__(self, workspace_root: Path):
        super().__init__()
        self._workspace_root = workspace_root
        self._locals: list[LocalStatus] = []
        self._remotes: dict[str, RemoteStatus] = {}
        self._deploy = "cm5" if sys.platform.startswith("linux") else "all"
        self._selected = ""
        self._busy = False
        self._status = ""
        self._activity: list[str] = []
        self._operation_steps: list[dict[str, str]] = []
        self._operation_progress = 0
        self._active_phase = ""
        self._operation_visible = False
        self._batch_current = 1
        self._batch_total = 1
        self._batch_project = ""
        self._lang = i18n.resolve_initial_lang()
        self._remoteResult.connect(self._on_remote_result)
        self._actionResult.connect(self._on_action_result)
        self._operationCheckpoint.connect(self._on_operation_checkpoint)
        self._batchProject.connect(self._on_batch_project)
        self.refresh(False)

    # -- QML-visible properties -----------------------------------------
    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._lang

    @Property(str, constant=True)
    def appVersion(self) -> str:
        return __version__

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=summaryChanged)
    def workspaceRoot(self) -> str:
        return str(self._workspace_root)

    @Property("QStringList", notify=activityChanged)
    def activity(self) -> list[str]:
        return self._activity[-8:]

    @Property("QVariantList", notify=operationChanged)
    def operationSteps(self) -> list[dict[str, str]]:
        return self._operation_steps

    @Property(int, notify=operationChanged)
    def operationProgress(self) -> int:
        return self._operation_progress

    @Property(str, notify=operationChanged)
    def operationDetail(self) -> str:
        if not self._active_phase:
            return self.text("checkpoint_waiting")
        current = next((step for step in self._operation_steps if step["id"] == self._active_phase), None)
        return current["detail"] if current else self.text("checkpoint_waiting")

    @Property(bool, notify=operationChanged)
    def operationVisible(self) -> bool:
        """Whether the action panel should present the last approved flow.

        Keeping the checkpoint evidence visible after a result lets an
        operator review it. Selecting a different project returns the panel
        to its normal, project-specific action controls.
        """
        return self._operation_visible

    @Property(str, notify=operationChanged)
    def operationHeading(self) -> str:
        if self._batch_total <= 1:
            return self.text("checkpoint_title")
        return self._t(
            "checkpoint_batch_title",
            current=self._batch_current,
            total=self._batch_total,
            project=self._batch_project,
        )

    @Property(str, notify=selectionChanged)
    def selectedProject(self) -> str:
        return self._selected or self.text("selected_project_none")

    @Property(bool, notify=selectionChanged)
    def canInstall(self) -> bool:
        selected = self._selected_status()
        return selected is not None and not selected.installed

    @Property(bool, notify=selectionChanged)
    def canUpdate(self) -> bool:
        selected = self._selected_status()
        if selected is None or not selected.installed or selected.version is None:
            return False
        remote = self._remotes.get(selected.entry.name)
        return remote is not None and remote.version is not None and selected.version < remote.version

    @Property(int, notify=summaryChanged)
    def missingCount(self) -> int:
        return sum(1 for item in self._locals if not item.installed)

    @Property(bool, notify=summaryChanged)
    def canInstallAll(self) -> bool:
        return self.missingCount > 0

    @Property(bool, notify=summaryChanged)
    def canUpdateAll(self) -> bool:
        return self.updateCount > 0

    @Property(int, notify=summaryChanged)
    def discoveredCount(self) -> int:
        return len(self._locals)

    @Property(int, notify=summaryChanged)
    def installedCount(self) -> int:
        return sum(1 for item in self._locals if item.installed)

    @Property(int, notify=summaryChanged)
    def updateCount(self) -> int:
        return sum(
            1 for item in self._locals
            if _state_key(item, self._remotes.get(item.entry.name)) == "state_outdated"
        )

    @Property("QVariantList", notify=deployOptionsChanged)
    def deployOptions(self) -> list[dict[str, str]]:
        return [
            {"key": key, "label": self._t("deploy_all", count=len(self._locals)) if key == "all" else self._t(f"deploy_{key}")}
            for key in DEPLOY_ORDER
        ]

    @Property("QVariantList", notify=projectsChanged)
    def projects(self) -> list[dict[str, object]]:
        ordered = sorted(
            self._locals,
            key=lambda item: (
                item.entry.family.casefold(),
                0 if item.entry.parent is None else 1,
                item.entry.name.casefold(),
            ),
        )
        visible: list[dict[str, object]] = []
        for item in ordered:
            entry = item.entry
            if self._deploy != "all" and entry.deploy != self._deploy:
                continue
            remote = self._remotes.get(entry.name)
            state_key = _state_key(item, remote)
            visible.append({
                "name": entry.name,
                "family": entry.family,
                "isChild": bool(entry.parent),
                "maturity": self.text(f"maturity_{entry.maturity}"),
                "role": self.text(f"role_{entry.role}"),
                "stack": entry.stack,
                "deploy": self.text(f"deploy_{entry.deploy}"),
                "local": str(item.version) if item.version else ("-" if not item.installed else "?"),
                "github": str(remote.version) if remote and remote.version else "-",
                "state": self.text(state_key),
                "stateKey": state_key,
                "notes": entry.notes or self.text("notes_empty"),
                "tech": ", ".join(entry.tech),
            })
        return visible

    # -- Localisation / selection ---------------------------------------
    @Slot(str, result=str)
    def text(self, key: str) -> str:
        return self._t(key)

    def _t(self, key: str, **kwargs: object) -> str:
        """Python-side translation helper; QML calls the no-keyword Slot."""
        return i18n.t(self._lang, key, **kwargs)

    @Slot(str)
    def setLanguage(self, language: str) -> None:
        if language not in {code for code, _label in i18n.LANGUAGES}:
            return
        self._lang = language
        i18n.save_lang_preference(language)
        self.languageChanged.emit()
        self.deployOptionsChanged.emit()
        self.projectsChanged.emit()
        self.summaryChanged.emit()

    @Slot(str)
    def setDeploy(self, deploy: str) -> None:
        if deploy in DEPLOY_ORDER:
            self._deploy = deploy
            self.projectsChanged.emit()

    @Slot(str)
    def selectProject(self, name: str) -> None:
        # Do not allow a second row to hide the evidence while an actual
        # install/update thread is still running. Once it ends, a new row is
        # precisely the operator's cue to return to the normal action panel.
        if self._busy and self._operation_visible:
            return
        self._selected = name if any(item.entry.name == name for item in self._locals) else ""
        if self._operation_visible:
            self._operation_visible = False
            self.operationChanged.emit()
        self.selectionChanged.emit()

    @Slot(str)
    def setWorkspaceUrl(self, url: str) -> None:
        path = QUrl(url).toLocalFile() if url.startswith("file:") else url
        if not path:
            return
        self._workspace_root = Path(path)
        self._append_activity(self.text("log_workspace_changed").format(path=self._workspace_root))
        self.summaryChanged.emit()
        self.refresh(False)

    @Slot()
    def openSelectedGithub(self) -> None:
        if self._selected:
            webbrowser.open(f"https://github.com/{GITHUB_OWNER}/{self._selected}")

    # -- Actual updater operations --------------------------------------
    @Slot(bool)
    def refresh(self, offline: bool) -> None:
        if self._busy:
            return
        self._set_busy(True, self.text("status_scanning"))
        self._append_activity(self.text("log_local_scan"))
        local_discovery = discover_workspace(self._workspace_root)
        self._locals = list(local_discovery.projects)
        self._remotes = {}
        self.projectsChanged.emit()
        self.summaryChanged.emit()
        self.selectionChanged.emit()
        self.deployOptionsChanged.emit()
        if offline:
            self._set_busy(False, self.text("status_ready_offline"))
            self._append_activity(self.text("log_offline_ready").format(projects=len(self._locals)))
            return
        self._status = self.text("status_checking_github")
        self.statusChanged.emit()
        self._append_activity(self.text("log_github_check"))

        def worker() -> None:
            try:
                discovery = discover_remote_projects()
                remotes = {status.entry.name: status for status in discovery.projects}
                errors: tuple[str, ...] = discovery.errors
            except RuntimeError as exc:
                remotes = fetch_all([status.entry for status in self._locals])
                errors = (f"Remote discovery unavailable: {exc}",)
            local_by_name = {status.entry.name: status for status in self._locals}
            entries = {name: status.entry for name, status in local_by_name.items()}
            entries.update({name: status.entry for name, status in remotes.items()})
            combined = [
                local_by_name.get(name, LocalStatus(entry=entry, path=self._workspace_root / name, installed=False, version=None))
                for name, entry in entries.items()
            ]
            self._remoteResult.emit(combined, remotes, errors)

        threading.Thread(target=worker, daemon=True, name="hydra-umc-updater-github").start()

    @Slot(str, bool)
    def performSelected(self, action: str, skip_build: bool) -> None:
        if self._busy:
            return
        selected = next((item for item in self._locals if item.entry.name == self._selected), None)
        if selected is None:
            self._append_activity(self.text("msg_select_project_first"))
            return
        if action == "install" and selected.installed:
            self._append_activity(self.text("msg_already_installed").format(name=selected.entry.name, path=selected.path))
            return
        if action == "update" and not selected.installed:
            self._append_activity(self.text("msg_not_installed_yet").format(name=selected.entry.name))
            return
        verb = self.text("action_installing" if action == "install" else "action_updating")
        self._start_operation(skip_build)
        self._set_busy(True, self.text("status_action_progress").format(verb=verb, name=selected.entry.name))
        self._append_activity(self.text("log_action_started").format(verb=verb, name=selected.entry.name))

        def worker() -> None:
            def report(phase: str, detail: str) -> None:
                self._operationCheckpoint.emit(phase, detail)

            self._actionResult.emit(
                selected.entry.name,
                install_or_update(selected.entry, self._workspace_root, build=not skip_build, progress=report),
            )

        threading.Thread(target=worker, daemon=True, name="hydra-umc-updater-action").start()

    @Slot(str, bool)
    def performBatch(self, action: str, skip_build: bool) -> None:
        """Run one operator-confirmed, sequential batch of safe actions.

        This is intentionally not background auto-maintenance. The user has
        explicitly selected Install-all-missing or Update-all-outdated in the
        GUI, and every child action still uses the same clone/fetch,
        anti-rollback and non-versioning build-test path as a single action.
        A failed project is recorded but does not prevent independent later
        projects from being checked, giving the operator a complete batch
        report without sacrificing any repository's fail-closed guardrails.
        """
        if self._busy:
            return
        if action == "install":
            targets = [item for item in self._locals if not item.installed]
        elif action == "update":
            targets = [
                item for item in self._locals
                if _state_key(item, self._remotes.get(item.entry.name)) == "state_outdated"
            ]
        else:
            return
        if not targets:
            self._append_activity(self.text("msg_batch_nothing_to_do"))
            return

        verb = self.text("action_installing" if action == "install" else "action_updating")
        self._start_operation(skip_build, batch_total=len(targets))
        self._set_busy(True, self._t("status_batch_progress", verb=verb, total=len(targets)))
        self._append_activity(self._t("log_batch_started", verb=verb, total=len(targets)))

        def worker() -> None:
            outcome: list[object] = []
            for index, selected in enumerate(targets, start=1):
                self._batchProject.emit(index, len(targets), selected.entry.name)

                def report(phase: str, detail: str, *, position: int = index, total: int = len(targets), name: str = selected.entry.name) -> None:
                    self._operationCheckpoint.emit(phase, f"[{position}/{total}] {name}: {detail}")

                outcome.extend(
                    install_or_update(
                        selected.entry,
                        self._workspace_root,
                        build=not skip_build,
                        progress=report,
                    )
                )
            self._actionResult.emit(self._t("batch_result_name", total=len(targets)), outcome)

        threading.Thread(target=worker, daemon=True, name="hydra-umc-updater-batch").start()

    @Slot(result=str)
    def selectedNotes(self) -> str:
        selected = next((item for item in self._locals if item.entry.name == self._selected), None)
        if selected is None:
            return self.text("note_default")
        entry = selected.entry
        tech = f"\n{self.text('note_tech').format(tech=', '.join(entry.tech))}" if entry.tech else ""
        return f"{entry.notes or self.text('notes_empty')}{tech}\n{self.text('note_build').format(build=entry.note or self.text('build_empty'))}"

    # -- Worker completions ----------------------------------------------
    @Slot(object, object, object)
    def _on_remote_result(self, locals_: object, remotes: object, errors: object) -> None:
        self._locals = list(locals_)  # type: ignore[arg-type]
        self._remotes = dict(remotes)  # type: ignore[arg-type]
        error_list = tuple(errors)  # type: ignore[arg-type]
        self.projectsChanged.emit()
        self.summaryChanged.emit()
        self.selectionChanged.emit()
        self.deployOptionsChanged.emit()
        self._set_busy(False, "; ".join(error_list[:2]) if error_list else self.text("status_ready"))
        self._append_activity(self.text("log_github_ready").format(projects=len(self._locals)))

    @Slot(str, object)
    def _on_action_result(self, name: str, results: object) -> None:
        outcome = list(results)  # type: ignore[arg-type]
        ok = all(result.ok for result in outcome)
        self._finish_operation(ok, outcome)
        self._set_busy(False, self.text("status_ready"))
        result_key = "log_result_ok" if ok else "log_result_failed"
        self._append_activity(self.text("log_action_finished").format(name=name, result=self.text(result_key)))
        self.refresh(False)

    @Slot(str, str)
    def _on_operation_checkpoint(self, phase: str, detail: str) -> None:
        step_index = next((index for index, step in enumerate(self._operation_steps) if step["id"] == phase), None)
        if step_index is None:
            return
        self._active_phase = phase
        for index, step in enumerate(self._operation_steps):
            if index < step_index and step["state"] != "skipped":
                step["state"] = "done"
            elif index == step_index and step["state"] != "skipped":
                step["state"] = "active"
        self._operation_steps[step_index]["detail"] = detail
        if self._batch_total > 1:
            phase_fraction = step_index / max(len(self._operation_steps) - 1, 1)
            self._operation_progress = int(((self._batch_current - 1 + phase_fraction) / self._batch_total) * 100)
        else:
            self._operation_progress = int((step_index / len(self._operation_steps)) * 100)
        self._append_activity(f"[{step_index + 1}/{len(self._operation_steps)}] {detail}")
        self.operationChanged.emit()

    @Slot(int, int, str)
    def _on_batch_project(self, current: int, total: int, name: str) -> None:
        self._batch_current = current
        self._batch_total = total
        self._batch_project = name
        self._active_phase = "preflight"
        for step in self._operation_steps:
            if step["state"] != "skipped":
                step["state"] = "pending"
                step["detail"] = self.text("checkpoint_waiting")
        if self._operation_steps:
            self._operation_steps[0]["state"] = "active"
        self._operation_progress = int(((current - 1) / total) * 100)
        self._append_activity(self._t("log_batch_project", current=current, total=total, name=name))
        self.operationChanged.emit()

    def _start_operation(self, skip_build: bool, *, batch_total: int = 1) -> None:
        steps = [
            ("preflight", "checkpoint_preflight"),
            ("source", "checkpoint_source"),
            ("validation", "checkpoint_validation"),
            ("build", "checkpoint_build_skipped" if skip_build else "checkpoint_build"),
            ("complete", "checkpoint_complete"),
        ]
        self._operation_steps = [
            {
                "id": phase,
                "label": self.text(label),
                "detail": self.text("checkpoint_waiting"),
                "state": "skipped" if phase == "build" and skip_build else "pending",
            }
            for phase, label in steps
        ]
        self._operation_progress = 0
        self._active_phase = "preflight"
        self._operation_visible = True
        self._batch_current = 1
        self._batch_total = batch_total
        self._batch_project = ""
        self.operationChanged.emit()

    def _finish_operation(self, ok: bool, outcome: list[object]) -> None:
        failed_step = next((result for result in outcome if not result.ok), None)
        if ok:
            for step in self._operation_steps:
                if step["state"] != "skipped":
                    step["state"] = "done"
            self._active_phase = "complete"
            self._operation_steps[-1]["detail"] = self.text("checkpoint_complete_detail")
            self._operation_progress = 100
        else:
            active = next((step for step in self._operation_steps if step["state"] == "active"), self._operation_steps[0])
            active["state"] = "failed"
            active["detail"] = failed_step.message if failed_step is not None else self.text("checkpoint_failed")
            self._active_phase = active["id"]
        for result in outcome:
            output = getattr(result, "output", "")
            if output:
                lines = [line.strip() for line in output.splitlines() if line.strip()]
                for line in lines[-4:]:
                    self._append_activity(f"  {line[:180]}")
        self.operationChanged.emit()

    def _set_busy(self, busy: bool, status: str) -> None:
        self._busy = busy
        self._status = status
        self.busyChanged.emit()
        self.statusChanged.emit()

    def _append_activity(self, text: str) -> None:
        self._activity.append(text.replace("\n", " "))
        self.activityChanged.emit()

    def _selected_status(self) -> LocalStatus | None:
        return next((item for item in self._locals if item.entry.name == self._selected), None)


def launch_qt_gui(workspace_root: Path) -> int:
    """Launch the QML desktop application and return its Qt event-loop code."""
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("HYDRA-UMC-UPDATER")
    app.setApplicationDisplayName("HYDRA-UMC Updater")
    # Windows receives a native .ico rendered from the official SVG identity
    # asset. The SVG is a safe fallback for a fresh source checkout where the
    # generated ICO has not yet been produced.
    project_root = Path(__file__).resolve().parents[2]
    icon = project_root / "images" / "HYDRA_UMC_ICON.ico"
    if not icon.is_file():
        icon = project_root / "images" / "HYDRA_UMC_ICON.svg"
    app.setWindowIcon(QIcon(str(icon)))
    engine = QQmlApplicationEngine()
    bridge = UpdaterBridge(workspace_root)
    engine.rootContext().setContextProperty("backend", bridge)
    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
