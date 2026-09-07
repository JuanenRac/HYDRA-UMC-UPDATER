# =============================================================================
# HYDRA-UMC-UPDATER - Ecosystem discovery catalog
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Small parser for the public JuanenRac ecosystem discovery catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .project_manifest import ECOSYSTEM_ID, MANIFEST_FILE


class CatalogValidationError(ValueError):
    """The discovery catalog is missing a required safe-routing field."""


@dataclass(frozen=True)
class EcosystemCatalog:
    schema_version: str
    ecosystem: str
    github_owner: str
    manifest_file: str
    dashboard_exclude: tuple[str, ...]


def parse_catalog(text: str) -> EcosystemCatalog:
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CatalogValidationError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise CatalogValidationError("catalog root must be an object")
    if data.get("schema_version") != "1.0":
        raise CatalogValidationError("schema_version must be '1.0'")
    if data.get("ecosystem") != ECOSYSTEM_ID:
        raise CatalogValidationError(f"ecosystem must be {ECOSYSTEM_ID!r}")
    owner = data.get("github_owner")
    if not isinstance(owner, str) or not owner.strip():
        raise CatalogValidationError("github_owner must be a non-empty string")
    if data.get("manifest_file") != MANIFEST_FILE:
        raise CatalogValidationError(f"manifest_file must be {MANIFEST_FILE!r}")
    excluded = data.get("dashboard_exclude")
    if not isinstance(excluded, list) or any(not isinstance(item, str) for item in excluded):
        raise CatalogValidationError("dashboard_exclude must be a string array")
    return EcosystemCatalog(
        schema_version="1.0",
        ecosystem=ECOSYSTEM_ID,
        github_owner=owner,
        manifest_file=MANIFEST_FILE,
        dashboard_exclude=tuple(excluded),
    )
