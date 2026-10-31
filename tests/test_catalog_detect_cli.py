# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_catalog_detect_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Characterization tests: ecosystem catalog parsing, workspace discovery and
the small helpers/branches of the CLI entry point. They pin today's behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_umc_updater import main as main_module
from hydra_umc_updater.detect import LocalStatus, discover_workspace, scan_workspace
from hydra_umc_updater.ecosystem_catalog import CatalogValidationError, parse_catalog
from hydra_umc_updater.project_manifest import ECOSYSTEM_ID, MANIFEST_FILE
from hydra_umc_updater.registry import ProjectEntry
from hydra_umc_updater.version_parse import Version


def _catalog(**overrides: object) -> str:
    data: dict[str, object] = {
        "schema_version": "1.0",
        "ecosystem": ECOSYSTEM_ID,
        "github_owner": "SomeOwner",
        "manifest_file": MANIFEST_FILE,
        "dashboard_exclude": ["A", "B"],
    }
    data.update(overrides)
    return json.dumps(data)


def test_catalog_valid_roundtrip() -> None:
    cat = parse_catalog(_catalog())
    assert cat.github_owner == "SomeOwner"
    assert cat.manifest_file == MANIFEST_FILE
    assert cat.dashboard_exclude == ("A", "B")
    assert cat.schema_version == "1.0"


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("{not json", "invalid JSON"),
        ("[]", "root must be an object"),
        (_catalog(schema_version="2.0"), "schema_version"),
        (_catalog(ecosystem="OTHER"), "ecosystem"),
        (_catalog(github_owner="  "), "github_owner"),
        (_catalog(github_owner=5), "github_owner"),
        (_catalog(manifest_file="x.json"), "manifest_file"),
        (_catalog(dashboard_exclude="nope"), "dashboard_exclude"),
        (_catalog(dashboard_exclude=["ok", 3]), "dashboard_exclude"),
    ],
)
def test_catalog_rejections(text: str, fragment: str) -> None:
    with pytest.raises(CatalogValidationError) as err:
        parse_catalog(text)
    assert fragment in str(err.value)


def _manifest(name: str, ecosystem: str = ECOSYSTEM_ID, version: str = "1.2.3") -> str:
    return json.dumps(
        {
            "schema_version": "1.0",
            "ecosystem": ecosystem,
            "name": name,
            "version": version,
            "role": "service",
            "stack": "python",
            "technologies": ["Python"],
            "deployment_target": "cm5",
            "maturity": "functional",
            "family": "Examples",
            "parent": None,
            "native_version": {"file": "pyproject.toml", "pattern": "version"},
            "build": "python -m x",
            "notes": "n",
        }
    )


def test_discover_missing_workspace_reports_error(tmp_path: Path) -> None:
    result = discover_workspace(tmp_path / "nope")
    assert result.projects == ()
    assert "workspace does not exist" in result.errors[0]


def test_discover_workspace_filters_by_manifest_and_ecosystem(tmp_path: Path) -> None:
    good = tmp_path / "HYDRA-UMC-GOOD"
    good.mkdir()
    (good / MANIFEST_FILE).write_text(_manifest("HYDRA-UMC-GOOD"), encoding="utf-8")
    other = tmp_path / "ARMOR-OTHER"
    other.mkdir()
    (other / MANIFEST_FILE).write_text(_manifest("ARMOR-OTHER", ecosystem="ARMOR"), encoding="utf-8")
    bad = tmp_path / "HYDRA-UMC-BAD"
    bad.mkdir()
    (bad / MANIFEST_FILE).write_text("{broken", encoding="utf-8")
    (tmp_path / "HYDRA-UMC-NOMANIFEST").mkdir()
    (tmp_path / "a-file.txt").write_text("x", encoding="utf-8")

    result = discover_workspace(tmp_path)
    names = [p.entry.name for p in result.projects]
    assert names == ["HYDRA-UMC-GOOD"]
    assert result.projects[0].installed is True
    assert str(result.projects[0].version) == "1.2.3"
    # a foreign-ecosystem manifest is rejected by the parser, so it is reported too
    assert len(result.errors) == 2
    assert any(e.startswith("ARMOR-OTHER: invalid manifest") for e in result.errors)
    assert any(e.startswith("HYDRA-UMC-BAD: invalid manifest") for e in result.errors)
    assert [s.entry.name for s in scan_workspace(tmp_path)] == ["HYDRA-UMC-GOOD"]


def test_discover_rejects_manifest_whose_name_differs_from_folder(tmp_path: Path) -> None:
    folder = tmp_path / "HYDRA-UMC-FOLDER"
    folder.mkdir()
    (folder / MANIFEST_FILE).write_text(_manifest("HYDRA-UMC-OTHERNAME"), encoding="utf-8")
    result = discover_workspace(tmp_path)
    assert result.projects == ()
    assert len(result.errors) == 1


def test_installed_as_package_detection() -> None:
    assert main_module._installed_as_package(Path("C:/py/Lib/site-packages/hydra_umc_updater/main.py"))
    assert main_module._installed_as_package(Path("/x/.venv/lib/main.py"))
    assert main_module._installed_as_package(Path("/usr/lib/dist-packages/x/main.py"))
    assert not main_module._installed_as_package(Path("/home/u/HYDRA-UMC-UPDATER/src/hydra_umc_updater/main.py"))


def test_default_workspace_root_environment_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(main_module.WORKSPACE_ENV, str(tmp_path))
    assert main_module.default_workspace_root() == tmp_path.resolve()


def test_default_workspace_root_installed_uses_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(main_module.WORKSPACE_ENV, raising=False)
    monkeypatch.setattr(main_module, "_installed_as_package", lambda _p: True)
    monkeypatch.chdir(tmp_path)
    assert main_module.default_workspace_root() == Path.cwd()


def test_default_workspace_root_checkout_uses_grandparent_of_src(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(main_module.WORKSPACE_ENV, raising=False)
    monkeypatch.setattr(main_module, "_installed_as_package", lambda _p: False)
    assert main_module.default_workspace_root() == Path(main_module.__file__).resolve().parents[3]


def _entry() -> ProjectEntry:
    return ProjectEntry(name="HYDRA-UMC-X", stack="python", version_file="v", pattern="", maturity="functional", role="service")


@pytest.mark.parametrize(
    "installed, local, remote_version, has_remote, expected",
    [
        (False, None, None, False, "not installed"),
        (True, None, None, False, "unknown (local)"),
        (True, Version(1, 0, 0), None, False, "installed (not checked)"),
        (True, Version(1, 0, 0), None, True, "installed, GitHub unknown (boom)"),
        (True, Version(1, 0, 0), Version(1, 0, 1), True, "OUTDATED"),
        (True, Version(1, 0, 2), Version(1, 0, 1), True, "ahead of GitHub"),
        (True, Version(1, 0, 1), Version(1, 0, 1), True, "up to date"),
    ],
)
def test_state_label(installed, local, remote_version, has_remote, expected) -> None:
    from hydra_umc_updater.github_client import RemoteStatus

    ls = LocalStatus(entry=_entry(), path=Path("x"), installed=installed, version=local)
    remote = RemoteStatus(entry=_entry(), version=remote_version, error="boom") if has_remote else None
    assert main_module._state_label(ls, remote) == expected


def _fake_local(tmp_path: Path):
    from hydra_umc_updater.detect import LocalDiscovery

    return LocalDiscovery(
        projects=(LocalStatus(entry=_entry(), path=tmp_path / "HYDRA-UMC-X", installed=True, version=Version(1, 0, 0)),),
        errors=(),
    )


def test_status_offline_table_and_notes(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: _fake_local(tmp_path))
    args = main_module.build_parser().parse_args(["status", "--offline", "--notes", "--workspace", str(tmp_path)])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "PROJECT" in out and "HYDRA-UMC-X" in out
    assert "1/1 installed, 0 outdated (GitHub not checked)" in out
    assert "(--offline: not checking GitHub" in out
    assert "(no notes recorded for this project yet)" in out


def test_status_json_offline_prints_only_json(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: _fake_local(tmp_path))
    args = main_module.build_parser().parse_args(["status", "--offline", "--json", "--workspace", str(tmp_path)])
    assert args.func(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["offline"] is True
    assert payload["projects"][0]["state"] == "installed (not checked)"
    assert payload["projects"][0]["github_version"] is None


def test_status_falls_back_to_raw_fetch_when_discovery_rate_limited(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    from hydra_umc_updater.github_client import RemoteStatus

    monkeypatch.setattr(main_module, "discover_workspace", lambda root: _fake_local(tmp_path))
    monkeypatch.setattr(main_module, "default_etag_cache", lambda: None)

    def boom(**_kw):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(main_module, "discover_remote_projects", boom)
    monkeypatch.setattr(main_module, "fetch_all", lambda entries: {e.name: RemoteStatus(entry=e, version=Version(2, 0, 0)) for e in entries})
    args = main_module.build_parser().parse_args(["status", "--workspace", str(tmp_path)])
    assert args.func(args) == 0
    cap = capsys.readouterr()
    assert "remote discovery unavailable: rate limited" in cap.err
    assert "OUTDATED" in cap.out
    assert "1 outdated" in cap.out
    assert "hydra-umc-updater update <project>" in cap.out


def test_install_unknown_project_fails(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    from hydra_umc_updater.github_client import RemoteDiscovery

    monkeypatch.setattr(main_module, "default_etag_cache", lambda: None)
    monkeypatch.setattr(main_module, "discover_remote_projects", lambda **kw: RemoteDiscovery(projects=(), errors=()))
    args = main_module.build_parser().parse_args(["install", "NOPE", "--workspace", str(tmp_path)])
    assert args.func(args) == 1
    assert "Unknown ecosystem project: 'NOPE'" in capsys.readouterr().err


def test_install_discovery_failure_returns_one(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module, "default_etag_cache", lambda: None)

    def boom(**_kw):
        raise RuntimeError("offline")

    monkeypatch.setattr(main_module, "discover_remote_projects", boom)
    args = main_module.build_parser().parse_args(["install", "X", "--workspace", str(tmp_path)])
    assert args.func(args) == 1
    assert "Unable to discover GitHub projects: offline" in capsys.readouterr().err


def test_update_of_missing_checkout_and_install_of_existing_are_refused(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    from hydra_umc_updater.detect import LocalDiscovery
    from hydra_umc_updater.github_client import RemoteDiscovery, RemoteStatus

    entry = _entry()
    monkeypatch.setattr(main_module, "default_etag_cache", lambda: None)
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(), errors=()))
    monkeypatch.setattr(
        main_module, "discover_remote_projects", lambda **kw: RemoteDiscovery(projects=(RemoteStatus(entry=entry, version=Version(1, 0, 0)),), errors=())
    )
    upd = main_module.build_parser().parse_args(["update", entry.name, "--workspace", str(tmp_path)])
    assert upd.func(upd) == 1
    assert "use `install`, not `update`" in capsys.readouterr().err

    (tmp_path / entry.name).mkdir()
    ins = main_module.build_parser().parse_args(["install", entry.name, "--workspace", str(tmp_path)])
    assert ins.func(ins) == 1
    assert "use `update`, not `install`" in capsys.readouterr().err


def test_prune_backups_rejects_negative_keep(capsys, tmp_path: Path) -> None:
    args = main_module.build_parser().parse_args(["prune-backups", "--keep", "-1", "--workspace", str(tmp_path)])
    assert args.func(args) == 1
    assert "--keep must not be negative" in capsys.readouterr().err


def test_prune_backups_dry_run_on_empty_workspace(capsys, tmp_path: Path) -> None:
    args = main_module.build_parser().parse_args(["prune-backups", "--dry-run", "--workspace", str(tmp_path)])
    assert args.func(args) == 0
    assert "0 of 0 backup(s) would be removed; kept the newest 2 of each project." in capsys.readouterr().out


def test_main_cli_without_command_prints_help(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--cli"])
    assert main_module.main() == 0
    assert "usage:" in capsys.readouterr().out


def test_main_cli_dispatches_subcommand(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--cli", "prune-backups", "--dry-run", "--workspace", str(tmp_path)])
    assert main_module.main() == 0


def test_workspace_from_gui_arguments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--workspace", str(tmp_path)])
    assert main_module._workspace_from_gui_arguments() == tmp_path.resolve()
    monkeypatch.setattr("sys.argv", ["prog"])
    assert main_module._workspace_from_gui_arguments() is None
