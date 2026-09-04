# =============================================================================
# HYDRA-UMC-UPDATER - Entry point: main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Runs on the real CM5, on the user's own Windows/Linux/macOS dev machine,
# or anywhere else with the same ecosystem checkout layout - every project
# as a sibling directory under one workspace root, same assumption build-
# frontend.sh/HYDRA-UMC-SUITE's own discovery already make.
#
# Bare invocation (no arguments, or double-clicked) launches the QML desktop
# GUI (qt_gui.py, PySide6/Qt Quick) on a workstation or CM5 desktop/VNC
# session.  The old Tkinter shell stays as a compatibility fallback only when
# the optional GUI package was not installed. `--cli` switches to the
# headless argparse CLI below, with three subcommands:
#   status              - what's installed, what version, what's on GitHub
#   install <project>   - clone + build ONE project that isn't installed yet
#   update  <project>   - pull + rebuild ONE project that IS installed
# install/update are deliberately separate from status and always take an
# explicit project name - there is no "update everything" - see
# install.py's own header comment for why.
#
# GUI imports are only attempted after --cli has been ruled out.  A genuinely
# headless CM5 therefore never needs Qt, tkinter or a display to run
# `hydra-umc-updater --cli status`.
# =============================================================================
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .detect import LocalStatus, discover_workspace
from .github_client import RemoteStatus, discover_remote_projects, fetch_all
from .install import install_or_update
from .version_parse import Version


def default_workspace_root() -> Path:
    """This project's own parent directory - correct as long as
    HYDRA-UMC-UPDATER itself was checked out the same way every other
    ecosystem project is (a sibling of the other 55 under one common
    parent) - the standard layout this whole tool assumes throughout.
    Always overridable with --workspace for anything else (a CM5 install
    under a different path, a CI checkout, ...)."""
    return Path(__file__).resolve().parents[3]


def _state_label(local: LocalStatus, remote: RemoteStatus | None) -> str:
    if not local.installed:
        return "not installed"
    if local.version is None:
        return "unknown (local)"
    if remote is None:
        return "installed (not checked)"
    if remote.version is None:
        return f"installed, GitHub unknown ({remote.error})"
    if local.version < remote.version:
        return "OUTDATED"
    if remote.version < local.version:
        return "ahead of GitHub"
    return "up to date"


def cmd_status(args: argparse.Namespace) -> int:
    workspace_root = Path(args.workspace).resolve() if args.workspace else default_workspace_root()
    # Real bug fixed here, found while adding --json: this line (and the
    # --offline notice below) printed to stdout unconditionally, ahead of
    # everything else - the exact opposite of what --json promises a
    # script piping this output into `json.loads()`. Every diagnostic
    # stdout print in this function is now gated on `not args.json`;
    # informational GitHub-check messages already went to stderr, so
    # those needed no change.
    if not args.json:
        print(f"Workspace root: {workspace_root}")
    local_discovery = discover_workspace(workspace_root)
    local_by_name = {status.entry.name: status for status in local_discovery.projects}

    remotes: dict[str, RemoteStatus] = {}
    if not args.offline:
        print("Checking GitHub repository manifests...", file=sys.stderr)
        try:
            remote_discovery = discover_remote_projects()
            remotes = {status.entry.name: status for status in remote_discovery.projects}
            for error in remote_discovery.errors:
                print(f"WARNING: {error}", file=sys.stderr)
        except RuntimeError as exc:
            # Public GitHub API quotas can be exhausted on a developer PC.
            # Raw version reads still let an existing local workspace report
            # updates; automatic discovery resumes when a token is available.
            print(f"WARNING: remote discovery unavailable: {exc}", file=sys.stderr)
            remotes = fetch_all([status.entry for status in local_discovery.projects])
    elif not args.json:
        print("(--offline: not checking GitHub - showing local state only)")

    entries = {name: status.entry for name, status in local_by_name.items()}
    entries.update({name: status.entry for name, status in remotes.items()})
    locals_ = [
        local_by_name.get(
            name,
            LocalStatus(entry=entry, path=workspace_root / name, installed=False, version=None),
        )
        for name, entry in sorted(entries.items(), key=lambda item: item[0].casefold())
    ]

    if args.json:
        # Real, scripting-friendly shape - every field the human-readable
        # table below also shows, plus the real local checkout path (not
        # printed by the table at all) - never a second, independently-
        # drifting summary of the same discovery data.
        payload = {
            "workspace_root": str(workspace_root),
            "offline": bool(args.offline),
            "projects": [
                {
                    "name": ls.entry.name,
                    "maturity": ls.entry.maturity,
                    "role": ls.entry.role,
                    "stack": ls.entry.stack,
                    "installed": ls.installed,
                    "path": str(ls.path),
                    "local_version": str(ls.version) if ls.version else None,
                    "github_version": str(remotes[ls.entry.name].version) if ls.entry.name in remotes and remotes[ls.entry.name].version else None,
                    "state": _state_label(ls, remotes.get(ls.entry.name)),
                }
                for ls in locals_
            ],
        }
        installed_count = sum(1 for ls in locals_ if ls.installed)
        outdated_count = sum(1 for ls in locals_ if _state_label(ls, remotes.get(ls.entry.name)) == "OUTDATED")
        payload["installed_count"] = installed_count
        payload["outdated_count"] = outdated_count
        payload["total"] = len(locals_)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    name_w = max((len(p.name) for p in entries.values()), default=7) + 2
    # Dynamic like name_w above - a fixed width silently ran stack values
    # like "python-qtquick" (14 chars) straight into the LOCAL column with
    # no separating space the moment a stack name grew past the old fixed 12.
    stack_w = max((len(p.stack) for p in entries.values()), default=5) + 2
    header = f"{'PROJECT':<{name_w}}{'MATURITY':<13}{'ROLE':<10}{'STACK':<{stack_w}}{'LOCAL':<10}{'GITHUB':<10}{'STATE'}"
    print(header)
    print("-" * len(header))

    outdated = 0
    for ls in locals_:
        remote = remotes.get(ls.entry.name)
        local_v = str(ls.version) if ls.version else ("-" if not ls.installed else "?")
        remote_v = str(remote.version) if remote and remote.version else ("-" if args.offline else "?")
        state = _state_label(ls, remote)
        if state == "OUTDATED":
            outdated += 1
        print(
            f"{ls.entry.name:<{name_w}}{ls.entry.maturity:<13}{ls.entry.role:<10}"
            f"{ls.entry.stack:<{stack_w}}{local_v:<10}{remote_v:<10}{state}"
        )

    print()
    installed_count = sum(1 for ls in locals_ if ls.installed)
    print(f"{installed_count}/{len(locals_)} installed, {outdated} outdated" + (" (GitHub not checked)" if args.offline else ""))
    if outdated:
        print("Run `hydra-umc-updater update <project>` to update one by hand - never automatic, see this tool's own README.")
    if args.notes:
        print("\nNotes (what's actually real per project, from its own manifest):")
        for ls in locals_:
            entry = ls.entry
            parent_suffix = f" (child of {entry.parent})" if entry.parent else ""
            print(f"\n{entry.name} [{entry.family}{parent_suffix}]")
            print(f"  {entry.notes or '(no notes recorded for this project yet)'}")
            if entry.tech:
                print(f"  Tech: {', '.join(entry.tech)}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    return _install_or_update(args, expect_installed=False)


def cmd_update(args: argparse.Namespace) -> int:
    return _install_or_update(args, expect_installed=True)


def _install_or_update(args: argparse.Namespace, *, expect_installed: bool) -> int:
    workspace_root = Path(args.workspace).resolve() if args.workspace else default_workspace_root()
    local_discovery = discover_workspace(workspace_root)
    local_by_name = {status.entry.name: status.entry for status in local_discovery.projects}
    entry = local_by_name.get(args.project)

    # GitHub discovery makes a just-added manifest project installable without
    # an updater release or a hard-coded registry row.
    if entry is None or not expect_installed:
        try:
            remote_discovery = discover_remote_projects()
        except RuntimeError as exc:
            print(f"Unable to discover GitHub projects: {exc}", file=sys.stderr)
            return 1
        remote_by_name = {status.entry.name: status.entry for status in remote_discovery.projects}
        entry = remote_by_name.get(args.project, entry)

    if entry is None:
        print(f"Unknown ecosystem project: {args.project!r}", file=sys.stderr)
        print("The project must expose a valid hydra-umc.project.json on GitHub.", file=sys.stderr)
        return 1

    path = workspace_root / entry.name
    already_installed = path.is_dir()
    if expect_installed and not already_installed:
        print(f"{entry.name} isn't installed yet at {path} - use `install`, not `update`, the first time.", file=sys.stderr)
        return 1
    if not expect_installed and already_installed:
        print(f"{entry.name} already exists at {path} - use `update`, not `install`, for an existing checkout.", file=sys.stderr)
        return 1

    if entry.note:
        print(f"Note: {entry.note}")
    print(f"{'Updating' if expect_installed else 'Installing'} {entry.name} into {workspace_root} ...")

    results = install_or_update(entry, workspace_root, build=not args.no_build)
    ok = all(r.ok for r in results)
    for r in results:
        print(("OK  " if r.ok else "FAIL ") + r.message)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydra-umc-updater --cli",
        description="Detects, installs, and manually updates the HYDRA-UMC/URTC ecosystem's 56 projects on this machine.",
    )
    parser.add_argument("--version", action="version", version=f"hydra-umc-updater {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    status_p = subparsers.add_parser("status", help="Show what's installed, its version, and the latest GitHub version of every project.")
    status_p.add_argument("--workspace", help="Workspace root to scan (default: this tool's own parent directory).")
    status_p.add_argument("--offline", action="store_true", help="Skip the GitHub check - local state only.")
    status_p.add_argument("--notes", action="store_true", help="Also print each project's real notes (family/parent, what's actually implemented, tech) below the table.")
    status_p.add_argument("--json", action="store_true", help="Machine-readable JSON instead of the human-readable table (ignores --notes).")
    status_p.set_defaults(func=cmd_status)

    install_p = subparsers.add_parser("install", help="Clone and build ONE project that isn't installed yet.")
    install_p.add_argument("project", help="Exact project name (see `status` for the full list).")
    install_p.add_argument("--workspace", help="Workspace root (default: this tool's own parent directory).")
    install_p.add_argument("--no-build", action="store_true", help="Clone only - skip running the project's own build script.")
    install_p.set_defaults(func=cmd_install)

    update_p = subparsers.add_parser("update", help="Pull and rebuild ONE project that's already installed.")
    update_p.add_argument("project", help="Exact project name (see `status` for the full list).")
    update_p.add_argument("--workspace", help="Workspace root (default: this tool's own parent directory).")
    update_p.add_argument("--no-build", action="store_true", help="Pull only - skip running the project's own build script.")
    update_p.set_defaults(func=cmd_update)

    return parser


def main() -> int:
    if "--cli" not in sys.argv:
        try:
            from .qt_gui import launch_qt_gui
        except ImportError:
            # A checkout can still run its original dependency-free desktop
            # shell before `pip install -e '.[gui]'` has been performed. This
            # is a compatibility bridge, not the preferred visual path.
            try:
                from .gui import launch_gui
            except ImportError:
                print("The Qt Quick GUI is not installed and tkinter is unavailable. "
                      "Use `--cli` on a headless system, or run the project build "
                      "to install the optional PySide6 GUI runtime.", file=sys.stderr)
            else:
                print("Qt Quick GUI runtime is not installed; starting the legacy "
                      "Tkinter fallback. Run build.bat/build.sh to enable the new "
                      "visual desktop interface.", file=sys.stderr)
                return launch_gui(default_workspace_root())
        else:
            return launch_qt_gui(default_workspace_root())

    argv = [a for a in sys.argv[1:] if a != "--cli"]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
