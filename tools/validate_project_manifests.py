#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-UPDATER - Validate universal project manifests in one workspace
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Validate repository-owned project manifests and native build versions.

Run this from a full sibling-checkout workspace. It deliberately compares the
manifest version to the language/firmware source still consumed by the native
compiler, so a manual metadata edit is easy while a version divergence is
never silently published to the dashboard.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(SCRIPT_ROOT / "src"))

from hydra_umc_updater.project_manifest import (  # noqa: E402
    MANIFEST_FILE,
    ManifestValidationError,
    ProjectManifest,
    parse_manifest,
)
from hydra_umc_updater.version_parse import parse_version  # noqa: E402


def main() -> int:
    manifests: dict[str, ProjectManifest] = {}
    errors: list[str] = []

    manifest_paths = sorted(WORKSPACE_ROOT.glob(f"*/{MANIFEST_FILE}"))
    for path in manifest_paths:
        project_name = path.parent.name
        try:
            manifest = parse_manifest(path.read_text(encoding="utf-8"), expected_name=project_name)
        except (OSError, ManifestValidationError) as exc:
            errors.append(f"{project_name}: invalid {MANIFEST_FILE}: {exc}")
            continue

        manifests[project_name] = manifest
        native_path = path.parent / manifest.native_version_file
        try:
            native_text = native_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{project_name}: cannot read native version source {manifest.native_version_file}: {exc}")
            continue

        native_version = parse_version(native_text, manifest.native_version_pattern)
        if native_version is None:
            errors.append(f"{project_name}: native version not found in {manifest.native_version_file}")
        elif str(native_version) != manifest.version:
            errors.append(
                f"{project_name}: manifest {manifest.version} != native {native_version} ({manifest.native_version_file})"
            )

    names = set(manifests)
    for manifest in manifests.values():
        if manifest.parent == manifest.name:
            errors.append(f"{manifest.name}: parent cannot reference itself")
        elif manifest.parent is not None and manifest.parent not in names:
            errors.append(f"{manifest.name}: parent {manifest.parent!r} is not an ecosystem project")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1

    print(f"MANIFEST_VALIDATION=PASS projects={len(manifests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
