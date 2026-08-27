#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-UPDATER - Audit universal repository manifests: migrate_project_manifests.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Audit a workspace after the one-time manifest migration.

Project metadata is not generated from a central Python table.  Each new
repository must publish its own valid ``hydra-umc.project.json``; this tool
only reports the manifests that are already present.  Use
``validate_project_manifests.py`` to validate their native build versions.
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
    parse_manifest,
)


def main() -> int:
    manifests = sorted(WORKSPACE_ROOT.glob(f"*/{MANIFEST_FILE}"))
    errors: list[str] = []
    for path in manifests:
        try:
            parse_manifest(path.read_text(encoding="utf-8"), expected_name=path.parent.name)
        except (OSError, ManifestValidationError) as exc:
            errors.append(f"{path.parent.name}: {exc}")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"MANIFEST_AUDIT=PASS projects={len(manifests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
