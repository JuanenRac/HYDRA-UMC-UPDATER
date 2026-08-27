# =============================================================================
# HYDRA-UMC-UPDATER - Windowed GUI: gui.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Tkinter/ttk, stdlib only - matches URTC-FLASHER/URTC-TESTER's own
# established GUI convention for this ecosystem (see those projects' own
# urtc_flasher.py/tester_gui.py) rather than introducing a second GUI
# toolkit (PySide6, etc.) that would cost this tool the "dependency-free"
# property its own README already commits to.
#
# This is the DEFAULT way to run this tool now (double-click friendly, on
# both the CM5 itself over a local desktop/VNC session and a developer's
# own Windows/Linux/macOS machine) - main.py only falls back to the old
# argparse CLI when --cli is passed, or when tkinter genuinely isn't
# available (a headless CM5 with no python3-tk installed), following the
# exact "if '--cli' not in sys.argv: import tkinter" pattern main.py
# itself now uses, copied from urtc_flasher.py's own header comment.
#
# One window, one Treeview table (Project / Maturity / Role / Stack /
# Deploy / Local / GitHub / State), a deploy-target filter, and
# Install/Update buttons that call straight into the same
# detect.py/github_client.py/install.py this tool's CLI already uses and
# this session already verified end-to-end - no separate GUI-only logic to
# drift out of sync with the CLI.
#
# v3: the tree is a REAL parent/child tree, not a flat list - each
# repository manifest declares the integration parent; top-level parents and
# their real children are nested directly under it via Treeview's own
# native parent/child support - matching the family/parent structure the
# ecosystem's own README "Project Catalog" tables already describe, now
# machine-readable instead of implicit in a markdown table's own grouping.
#
# Also v3: real, complete language support (7 languages, see i18n.py) -
# a language Combobox next to the deploy filter switches every real
# widget's own text live (labels, buttons, column headings, status/state
# text, message boxes), not just at startup. `--cli` mode (main.py) stays
# English-only on purpose - see i18n.py's own module docstring for why.
# =============================================================================
from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

from . import __version__, i18n
from .detect import LocalStatus, discover_workspace
from .github_client import RemoteStatus, discover_remote_projects, fetch_all
from .install import install_or_update
from .registry import ProjectEntry

#: Order matters - shown left-to-right in the filter dropdown, "all" first.
#: Real labels come from i18n.t(lang, f"deploy_{key}") / "deploy_all" at
#: render time, not hardcoded here - see UpdaterGUI._deploy_label().
DEPLOY_ORDER = ["all", "cm5", "user-pc", "mobile", "wearable"]

#: The four manifest maturity values, in the same order as the dashboard.
MATURITY_KEYS = ("production", "established", "functional", "scaffolding")


def _default_deploy_filter() -> str:
    """Linux is the real CM5's own OS - default to showing only what
    actually belongs there. Anywhere else (a developer's Windows/macOS
    machine) defaults to showing everything, since "what am I even
    supposed to do with each of these 44 repos" is exactly the question
    the deploy field answers for a dev machine. Always changeable by hand
    from the dropdown regardless of platform - this is just a starting
    point, never a restriction (the deployment target comes from each
    repository manifest)."""
    return "cm5" if sys.platform.startswith("linux") else "all"


def _state_key(local: LocalStatus, remote: RemoteStatus | None) -> str:
    """Returns an i18n.py translation KEY (not human text) - the real
    state text itself is resolved at render time via i18n.t(lang, key),
    so switching languages later doesn't need this logic to run again."""
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


class UpdaterGUI:
    def __init__(self, root: tk.Tk, workspace_root: Path):
        self.root = root
        self.workspace_root = workspace_root
        self.locals_: list[LocalStatus] = []
        self.remotes: dict[str, RemoteStatus] = {}
        self._work_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._busy = False
        self.lang = i18n.resolve_initial_lang()

        root.title(f"HYDRA-UMC-UPDATER {__version__}")
        root.geometry("1040x580")
        root.minsize(820, 440)

        self._build_widgets()
        self._apply_language(self.lang, rerender=False)  # widgets exist now, no data to render yet
        self.root.after(100, self._poll_queue)
        self._refresh(offline=True)  # instant local-only pass on startup, GitHub check follows automatically

    def t(self, key: str, **kwargs: object) -> str:
        return i18n.t(self.lang, key, **kwargs)

    # -- Labels that depend on the current language, not hardcoded English --

    def _deploy_label(self, key: str) -> str:
        if key == "all":
            return self.t("deploy_all", count=len(self.locals_))
        return self.t(f"deploy_{key}")

    def _maturity_label(self, key: str) -> str:
        return self.t(f"maturity_{key}") if key in MATURITY_KEYS else key

    def _role_label(self, key: str) -> str:
        return self.t(f"role_{key}")

    # -- Widget layout -------------------------------------------------
    def _build_widgets(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(side="top", fill="x")

        self.workspace_lbl = ttk.Label(top, text="")
        self.workspace_lbl.pack(side="left")

        self.show_lbl = ttk.Label(top, text="")
        self.show_lbl.pack(side="left", padx=(16, 2))
        self.filter_var = tk.StringVar()
        filter_box = ttk.Combobox(top, textvariable=self.filter_var, state="readonly", width=22)
        filter_box.pack(side="left")
        filter_box.bind("<<ComboboxSelected>>", lambda _e: self._render_rows())
        self.filter_box = filter_box

        self.offline_var = tk.BooleanVar(value=False)
        self.offline_chk = ttk.Checkbutton(top, text="", variable=self.offline_var)
        self.offline_chk.pack(side="left", padx=(16, 0))

        self.refresh_btn = ttk.Button(top, text="", command=lambda: self._refresh(offline=self.offline_var.get()))
        self.refresh_btn.pack(side="right")

        self.lang_lbl = ttk.Label(top, text="")
        self.lang_lbl.pack(side="right", padx=(0, 6))
        self.lang_var = tk.StringVar()
        self._lang_by_label = {label: code for code, label in i18n.LANGUAGES}
        lang_box = ttk.Combobox(top, textvariable=self.lang_var, state="readonly",
                                 values=[label for _code, label in i18n.LANGUAGES], width=16)
        lang_box.pack(side="right", padx=(0, 12))
        lang_box.bind("<<ComboboxSelected>>", self._on_lang_selected)
        self.lang_box = lang_box

        columns = ("maturity", "role", "stack", "deploy", "local", "github", "state")
        self.tree = ttk.Treeview(self.root, columns=columns, show="tree headings", selectmode="browse")
        self.tree.column("#0", width=250)
        self.tree.column("maturity", width=90, anchor="center")
        self.tree.column("role", width=70, anchor="center")
        self.tree.column("stack", width=80, anchor="center")
        self.tree.column("deploy", width=130, anchor="center")
        self.tree.column("local", width=80, anchor="center")
        self.tree.column("github", width=80, anchor="center")
        self.tree.column("state", width=170)
        self.tree.tag_configure("outdated", foreground="#b03030")
        self.tree.tag_configure("not_installed", foreground="#888888")
        # Maturity color-coding, same 4-level convention as the public
        # dashboard (generate_dashboard.py's own MATURITY_CLASSES) -
        # applied as a row tag alongside (not instead of) outdated/
        # not_installed above, see _render_rows's own tag ordering for
        # which one wins when a row qualifies for more than one.
        self.tree.tag_configure("maturity_production", foreground="#0f766e")
        self.tree.tag_configure("maturity_established", foreground="#4338ca")
        self.tree.tag_configure("maturity_scaffolding", foreground="#b45309")
        self.tree.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))

        bottom = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        bottom.pack(side="top", fill="x")
        self.note_var = tk.StringVar()
        ttk.Label(bottom, textvariable=self.note_var, wraplength=760, justify="left").pack(side="top", fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btns = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        btns.pack(side="top", fill="x")
        self.install_btn = ttk.Button(btns, text="", command=self._install_selected)
        self.install_btn.pack(side="left")
        self.update_btn = ttk.Button(btns, text="", command=self._update_selected)
        self.update_btn.pack(side="left", padx=(8, 0))
        self.no_build_var = tk.BooleanVar(value=False)
        self.skip_build_chk = ttk.Checkbutton(btns, text="", variable=self.no_build_var)
        self.skip_build_chk.pack(side="left", padx=(16, 0))

        status = ttk.Frame(self.root, padding=(8, 0, 8, 6))
        status.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar()
        ttk.Label(status, textvariable=self.status_var).pack(side="left")

    # -- Language ----------------------------------------------------------

    def _on_lang_selected(self, _event=None) -> None:
        selected_label = self.lang_var.get()
        lang = self._lang_by_label.get(selected_label)
        if lang is None or lang == self.lang:
            return
        self.lang = lang
        i18n.save_lang_preference(lang)
        self._apply_language(lang)

    def _apply_language(self, lang: str, *, rerender: bool = True) -> None:
        """Re-labels every real widget for real, in place - not a
        restart-required setting. `rerender=False` only at __init__ time,
        before self.locals_ has anything in it yet to redraw."""
        self.lang = lang

        self.workspace_lbl.config(text=self.t("workspace_label", path=self.workspace_root))
        self.show_lbl.config(text=self.t("show_label"))
        self.offline_chk.config(text=self.t("offline_checkbox"))
        self.refresh_btn.config(text=self.t("refresh_button"))
        self.lang_lbl.config(text=self.t("lang_label"))
        self.install_btn.config(text=self.t("install_button"))
        self.update_btn.config(text=self.t("update_button"))
        self.skip_build_chk.config(text=self.t("skip_build_checkbox"))

        self.tree.heading("#0", text=self.t("col_project"))
        self.tree.heading("maturity", text=self.t("col_maturity"))
        self.tree.heading("role", text=self.t("col_role"))
        self.tree.heading("stack", text=self.t("col_stack"))
        self.tree.heading("deploy", text=self.t("col_deploy"))
        self.tree.heading("local", text=self.t("col_local"))
        self.tree.heading("github", text=self.t("col_github"))
        self.tree.heading("state", text=self.t("col_state"))

        self._refresh_deploy_filter()

        self.lang_box.config(values=[label for _code, label in i18n.LANGUAGES])
        own_label = next((label for code, label in i18n.LANGUAGES if code == lang), lang)
        self.lang_var.set(own_label)

        if not self._busy:
            self.status_var.set(self.t("status_ready"))

        if rerender:
            # _render_rows() re-translates the notes panel itself now (it
            # restores the real selection first) - see its own docstring.
            self._render_rows()
        else:
            # __init__'s first call: no data to render yet, but note_var
            # still needs its first real (translated) value instead of
            # staying blank until the first language switch or selection.
            self._on_select()

    def _refresh_deploy_filter(self) -> None:
        """Rebuilds the deploy filter's labels/values from the current
        self.locals_ - the "all" label embeds a live project count
        (_deploy_label), so this must re-run whenever self.locals_
        changes, not just on a language switch. Real bug found via live
        testing: the combobox showed "All 0 projects" from __init__'s
        pre-data call and stayed wrong through both the offline and
        online refresh passes, only correcting itself the next time a
        language switch happened to also call this rebuild."""
        previous_key = self._filter_by_label.get(self.filter_var.get(), _default_deploy_filter()) \
            if getattr(self, "_filter_by_label", None) else _default_deploy_filter()
        deploy_labels = [self._deploy_label(key) for key in DEPLOY_ORDER]
        self._filter_by_label = {self._deploy_label(key): key for key in DEPLOY_ORDER}
        self.filter_box.config(values=deploy_labels)
        self.filter_var.set(self._deploy_label(previous_key))

    # -- Data / refresh --------------------------------------------------
    def _refresh(self, *, offline: bool) -> None:
        if self._busy:
            return
        self._set_busy(True, self.t("status_scanning"))
        local_discovery = discover_workspace(self.workspace_root)
        self.locals_ = list(local_discovery.projects)
        self.remotes = {}
        self._refresh_deploy_filter()
        self._render_rows()

        if offline:
            self._set_busy(False, self.t("status_ready_offline"))
            return

        self.status_var.set(self.t("status_checking_github"))

        def worker():
            try:
                discovery = discover_remote_projects()
                remotes = {status.entry.name: status for status in discovery.projects}
                errors = discovery.errors
            except RuntimeError as exc:
                remotes = fetch_all([status.entry for status in self.locals_])
                errors = (f"Remote discovery unavailable: {exc}",)
            local_by_name = {status.entry.name: status for status in self.locals_}
            entries = {name: status.entry for name, status in local_by_name.items()}
            entries.update({name: status.entry for name, status in remotes.items()})
            combined = [
                local_by_name.get(
                    name,
                    LocalStatus(entry=entry, path=self.workspace_root / name, installed=False, version=None),
                )
                for name, entry in entries.items()
            ]
            combined.sort(key=lambda status: (status.entry.family.casefold(), 0 if status.entry.parent is None else 1, status.entry.name.casefold()))
            self._work_queue.put(("remotes", (combined, remotes, errors)))

        threading.Thread(target=worker, daemon=True).start()

    def _render_rows(self) -> None:
        # A full delete()+reinsert() below necessarily drops Treeview's
        # own selection (there's no "update in place" for a row that
        # might have moved family/parent) - real bug found while testing
        # a real language switch: the notes panel silently reverted to
        # its "nothing selected" placeholder even though the same real
        # project was still logically "selected" from the user's own
        # perspective. Remembering the selected iid(s) here and
        # reselecting them below (if they still exist in the new render -
        # they might not, if a filter change or family regrouping
        # legitimately removed that row) fixes this for every caller of
        # _render_rows(), not just the language switch that surfaced it.
        previously_selected = self.tree.selection()

        self.tree.delete(*self.tree.get_children())
        wanted = self._filter_by_label.get(self.filter_var.get(), "all")

        inserted: set[str] = set()

        # Real bug found via live testing: discover_workspace() only sorts
        # by folder name, which frequently is NOT "parent before children"
        # (e.g. "HYDRA-UMC-ANDROID-CONTROL" sorts before its own parent
        # "HYDRA-UMC-SERVER"). This single insert pass needs a project's
        # parent to already be in `inserted` or it silently falls back to a
        # top-level row - with plain self.locals_ order, 4 of
        # HYDRA-UMC-SERVER's 6 real children were orphaned to the top level
        # every time. Sorting here (family, parent-first, name) - the same
        # key the online _refresh() worker already applies to `combined` -
        # makes this correct regardless of self.locals_'s own order, for
        # every caller of _render_rows() (offline refresh, a filter change,
        # a language switch), not just the one that first surfaced it.
        ordered = sorted(
            self.locals_,
            key=lambda ls: (ls.entry.family.casefold(), 0 if ls.entry.parent is None else 1, ls.entry.name.casefold()),
        )
        # A child whose own parent got filtered out (different deploy
        # target than the one selected) falls back to a top-level row
        # instead of erroring on a parent iid that doesn't exist.
        for ls in ordered:
            if wanted != "all" and ls.entry.deploy != wanted:
                continue

            entry = ls.entry
            remote = self.remotes.get(entry.name)
            local_v = str(ls.version) if ls.version else ("-" if not ls.installed else "?")
            github_v = str(remote.version) if remote and remote.version else "-"
            state_key = _state_key(ls, remote)
            state = self.t(state_key)

            maturity_tag = f"maturity_{entry.maturity}" if entry.maturity in ("production", "established", "scaffolding") else ""
            status_tag = "outdated" if state_key == "state_outdated" else ("not_installed" if not ls.installed else "")
            # Outdated/not-installed status wins visually over the
            # maturity color - both real facts about this row, but "this
            # needs your attention right now" outranks "here's its
            # general maturity level" when they'd otherwise fight over
            # the same foreground color.
            tags = tuple(t for t in (status_tag, maturity_tag if not status_tag else "") if t)

            parent_iid = entry.parent if (entry.parent and entry.parent in inserted) else ""

            self.tree.insert(
                parent_iid, "end", iid=entry.name, text=entry.name,
                values=(
                    self._maturity_label(entry.maturity),
                    self._role_label(entry.role),
                    entry.stack,
                    self._deploy_label(entry.deploy),
                    local_v, github_v, state,
                ),
                tags=tags,
            )
            inserted.add(entry.name)

        # Family/parent rows start expanded - the whole point of the real
        # tree is to see the family grouping at a glance, not to hide it
        # behind a manual expand click on first load.
        for iid in self.tree.get_children(""):
            self.tree.item(iid, open=True)

        # Restore whatever was really selected before this render, for
        # every iid that's still real in the new tree (see the comment at
        # the top of this method for why this needed fixing).
        still_real = tuple(iid for iid in previously_selected if iid in inserted)
        if still_real:
            self.tree.selection_set(still_real)

        # selection_set() firing <<TreeviewSelect>> is real but not
        # guaranteed identically across every Tk build/platform - calling
        # this directly, rather than trusting the virtual event, is what
        # actually closes the real bug this method's own docstring above
        # describes, for every caller of _render_rows() rather than just
        # the one that first surfaced it.
        self._on_select()

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            self.note_var.set(self.t("note_default"))
            return
        entry = next((ls.entry for ls in self.locals_ if ls.entry.name == sel[0]), None)
        if entry is None:
            self.note_var.set(self.t("note_default"))
            return
        parent_suffix = f" · {self.t('note_child_of', parent=entry.parent)}" if entry.parent else ""
        tech_suffix = f" · {self.t('note_tech', tech=', '.join(entry.tech))}" if entry.tech else ""
        notes = entry.notes or self.t("notes_empty")
        build = entry.note or self.t("build_empty")
        self.note_var.set(f"[{entry.family}{parent_suffix}] {notes}{tech_suffix}\n{self.t('note_build', build=build)}")

    # -- Install / update -------------------------------------------------
    def _selected_local(self) -> LocalStatus | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("HYDRA-UMC-UPDATER", self.t("msg_select_project_first"))
            return None
        return next((ls for ls in self.locals_ if ls.entry.name == sel[0]), None)

    def _install_selected(self) -> None:
        ls = self._selected_local()
        if ls is None:
            return
        if ls.installed:
            messagebox.showwarning("HYDRA-UMC-UPDATER", self.t("msg_already_installed", name=ls.entry.name, path=ls.path))
            return
        self._run_install_or_update(ls, verb_key="action_installing")

    def _update_selected(self) -> None:
        ls = self._selected_local()
        if ls is None:
            return
        if not ls.installed:
            messagebox.showwarning("HYDRA-UMC-UPDATER", self.t("msg_not_installed_yet", name=ls.entry.name))
            return
        self._run_install_or_update(ls, verb_key="action_updating")

    def _run_install_or_update(self, ls: LocalStatus, *, verb_key: str) -> None:
        if self._busy:
            return
        verb = self.t(verb_key)
        if not messagebox.askyesno(
            "HYDRA-UMC-UPDATER",
            self.t("msg_confirm_action", verb=verb, name=ls.entry.name, workspace=self.workspace_root),
        ):
            return
        self._set_busy(True, self.t("status_action_progress", verb=verb, name=ls.entry.name))
        build = not self.no_build_var.get()

        def worker():
            results = install_or_update(ls.entry, self.workspace_root, build=build)
            self._work_queue.put(("install_done", (ls.entry.name, results)))

        threading.Thread(target=worker, daemon=True).start()

    # -- Background-thread -> main-thread bridge --------------------------
    def _set_busy(self, busy: bool, status: str) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.refresh_btn.config(state=state)
        self.install_btn.config(state=state)
        self.update_btn.config(state=state)
        self.status_var.set(status)

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._work_queue.get_nowait()
                if kind == "progress":
                    self.status_var.set(str(payload))
                elif kind == "remotes":
                    locals_, remotes, errors = payload  # type: ignore[misc]
                    self.locals_ = locals_
                    self.remotes = remotes
                    if errors:
                        self.status_var.set("; ".join(str(error) for error in errors[:2]))
                    self._refresh_deploy_filter()
                    self._render_rows()
                    self._set_busy(False, self.t("status_ready"))
                elif kind == "install_done":
                    name, results = payload  # type: ignore[misc]
                    ok = all(r.ok for r in results)
                    lines = "\n".join(("OK  " if r.ok else "FAIL ") + r.message for r in results)
                    self._set_busy(False, self.t("status_ready"))
                    (messagebox.showinfo if ok else messagebox.showerror)(
                        "HYDRA-UMC-UPDATER", f"{name}:\n\n{lines}")
                    self._refresh(offline=self.offline_var.get())
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def launch_gui(workspace_root: Path) -> int:
    root = tk.Tk()
    UpdaterGUI(root, workspace_root)
    root.mainloop()
    return 0
