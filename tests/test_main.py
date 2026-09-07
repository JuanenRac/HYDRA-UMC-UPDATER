# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

from hydra_umc_updater import main as main_module
from hydra_umc_updater.detect import LocalDiscovery, LocalStatus
from hydra_umc_updater.github_client import RemoteDiscovery, RemoteStatus
from hydra_umc_updater.main import build_parser
from hydra_umc_updater.registry import ProjectEntry
from hydra_umc_updater.version_parse import Version


def test_status_command_parses() -> None:
    args = build_parser().parse_args(["status"])
    assert args.command == "status"
    assert args.json is False


def test_status_json_flag_parses() -> None:
    args = build_parser().parse_args(["status", "--json"])
    assert args.json is True


def test_status_json_output_is_real_machine_readable_json(monkeypatch, capsys, tmp_path) -> None:
    """Real end-to-end of cmd_status's own --json branch, against fake
    (not network/filesystem) local+remote discovery - discover_workspace/
    discover_remote_projects already have their own real coverage
    elsewhere; this test is about the CLI's own JSON shape."""
    installed_entry = ProjectEntry(name="HYDRA-UMC-SDK", stack="python", version_file="pyproject.toml", pattern="", maturity="established", role="library")
    missing_entry = ProjectEntry(name="HYDRA-UMC-GHOST", stack="python", version_file="pyproject.toml", pattern="", maturity="scaffolding", role="service")

    local_discovery = LocalDiscovery(
        projects=(
            LocalStatus(entry=installed_entry, path=tmp_path / "HYDRA-UMC-SDK", installed=True, version=Version(0, 0, 2)),
        ),
        errors=(),
    )
    remote_discovery = RemoteDiscovery(
        projects=(
            RemoteStatus(entry=installed_entry, version=Version(0, 0, 3)),
            RemoteStatus(entry=missing_entry, version=Version(1, 0, 0)),
        ),
        errors=(),
    )
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: local_discovery)
    monkeypatch.setattr(main_module, "discover_remote_projects", lambda: remote_discovery)

    args = build_parser().parse_args(["status", "--json", "--workspace", str(tmp_path)])
    exit_code = args.func(args)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace_root"] == str(tmp_path)
    assert payload["total"] == 2
    assert payload["installed_count"] == 1
    assert payload["outdated_count"] == 1
    by_name = {p["name"]: p for p in payload["projects"]}
    assert by_name["HYDRA-UMC-SDK"]["installed"] is True
    assert by_name["HYDRA-UMC-SDK"]["local_version"] == "0.0.2"
    assert by_name["HYDRA-UMC-SDK"]["github_version"] == "0.0.3"
    assert by_name["HYDRA-UMC-SDK"]["state"] == "OUTDATED"
    assert by_name["HYDRA-UMC-GHOST"]["installed"] is False
    assert by_name["HYDRA-UMC-GHOST"]["local_version"] is None
