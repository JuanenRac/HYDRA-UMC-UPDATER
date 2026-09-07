# =============================================================================
# HYDRA-UMC-UPDATER - Local installation detection: detect.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# "Which ecosystem repositories are actually checked out on this machine?"
# Discovery reads repository-owned manifests; it never contains a fixed
# project list.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .project_manifest import ECOSYSTEM_ID, MANIFEST_FILE, ManifestValidationError, parse_manifest
from .registry import ProjectEntry, entry_from_manifest
from .version_parse import Version


@dataclass
class LocalStatus:
    entry: ProjectEntry
    #: Absolute path this project would live at under the scanned workspace root.
    path: Path
    #: True if `path` exists as a directory - independent of whether a
    #: version could actually be parsed out of it (a checkout mid-clone, or
    #: one whose version file got renamed upstream, still "exists").
    installed: bool
    #: None when not installed, or installed but the version file wasn't
    #: found/didn't match `entry.pattern` - callers show "unknown" for that,
    #: never a crash.
    version: Version | None


@dataclass(frozen=True)
class LocalDiscovery:
    """Repository-owned local projects discovered without a fixed registry list."""

    projects: tuple[LocalStatus, ...]
    errors: tuple[str, ...]


def discover_workspace(workspace_root: Path) -> LocalDiscovery:
    """Discover local HYDRA-UMC repositories by their root manifest.

    A folder name alone is never enough to join the ecosystem. This prevents
    unrelated local folders from being mistaken for an installable project.
    """
    projects: list[LocalStatus] = []
    errors: list[str] = []
    if not workspace_root.is_dir():
        return LocalDiscovery(projects=(), errors=(f"workspace does not exist: {workspace_root}",))

    for project_path in sorted(workspace_root.iterdir(), key=lambda path: path.name.casefold()):
        if not project_path.is_dir():
            continue
        manifest_path = project_path / MANIFEST_FILE
        if not manifest_path.is_file():
            continue
        try:
            manifest = parse_manifest(manifest_path.read_text(encoding="utf-8"), expected_name=project_path.name)
        except (OSError, ManifestValidationError) as exc:
            errors.append(f"{project_path.name}: invalid manifest: {exc}")
            continue
        if manifest.ecosystem != ECOSYSTEM_ID:
            continue
        entry = entry_from_manifest(manifest)
        major, minor, patch = (int(part) for part in manifest.version.split("."))
        projects.append(
            LocalStatus(
                entry=entry,
                path=project_path,
                installed=True,
                version=Version(major, minor, patch),
            )
        )

    return LocalDiscovery(projects=tuple(projects), errors=tuple(errors))


def scan_workspace(workspace_root: Path) -> list[LocalStatus]:
    """Compatibility alias for manifest-only local discovery."""
    return list(discover_workspace(workspace_root).projects)
