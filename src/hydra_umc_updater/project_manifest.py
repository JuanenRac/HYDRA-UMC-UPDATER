# =============================================================================
# HYDRA-UMC-UPDATER - Universal repository manifest validation
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Validation for the canonical ``hydra-umc.project.json`` repository file.

The manifest is intentionally dependency-free JSON so it can be read on a
developer PC, a CM5, GitHub Actions or directly from GitHub raw content.
It describes public project metadata and the release version only; secrets,
machine-specific paths and credentials never belong in it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


MANIFEST_FILE = "hydra-umc.project.json"
SCHEMA_VERSION = "1.0"
ECOSYSTEM_ID = "HYDRA-UMC"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
VALID_ROLES = frozenset({"api", "ui", "cli", "firmware", "library", "service", "tool"})
VALID_MATURITY = frozenset({"scaffolding", "functional", "established", "production"})
VALID_DEPLOYMENT_TARGETS = frozenset({"cm5", "user-pc", "mobile", "wearable"})


class ManifestValidationError(ValueError):
    """A manifest is syntactically valid JSON but violates the v1 contract."""


@dataclass(frozen=True)
class ProjectManifest:
    """Validated public metadata owned by one repository."""

    schema_version: str
    ecosystem: str
    name: str
    version: str
    role: str
    stack: str
    technologies: tuple[str, ...]
    deployment_target: str
    maturity: str
    family: str
    parent: str | None
    native_version_file: str
    native_version_pattern: str | dict[str, str]
    build: str
    notes: str


def _require_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} must be a non-empty string")
    return value


def parse_manifest(text: str, *, expected_name: str | None = None) -> ProjectManifest:
    """Parse and validate a v1 manifest without a third-party JSON Schema lib."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"invalid JSON: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ManifestValidationError("manifest root must be an object")

    expected_fields = {
        "schema_version", "ecosystem", "name", "version", "role", "stack", "technologies",
        "deployment_target", "maturity", "family", "parent", "native_version", "build", "notes",
    }
    unknown = sorted(set(data) - expected_fields)
    missing = sorted(expected_fields - set(data))
    if missing:
        raise ManifestValidationError("missing field(s): " + ", ".join(missing))
    if unknown:
        raise ManifestValidationError("unknown field(s): " + ", ".join(unknown))

    schema_version = _require_string(data, "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ManifestValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}, got {schema_version!r}"
        )

    ecosystem = _require_string(data, "ecosystem")
    if ecosystem != ECOSYSTEM_ID:
        raise ManifestValidationError(
            f"ecosystem must be {ECOSYSTEM_ID!r}, got {ecosystem!r}"
        )

    name = _require_string(data, "name")
    if expected_name is not None and name != expected_name:
        raise ManifestValidationError(
            f"name {name!r} does not match expected repository {expected_name!r}"
        )

    version = _require_string(data, "version")
    if not VERSION_RE.fullmatch(version):
        raise ManifestValidationError("version must use MAJOR.MINOR.PATCH")

    role = _require_string(data, "role")
    if role not in VALID_ROLES:
        raise ManifestValidationError(f"unsupported role: {role!r}")

    stack = _require_string(data, "stack")
    raw_technologies = data.get("technologies")
    if (
        not isinstance(raw_technologies, list)
        or not raw_technologies
        or any(not isinstance(item, str) or not item.strip() for item in raw_technologies)
        or len(set(raw_technologies)) != len(raw_technologies)
    ):
        raise ManifestValidationError("technologies must be a non-empty unique string array")

    deployment_target = _require_string(data, "deployment_target")
    if deployment_target not in VALID_DEPLOYMENT_TARGETS:
        raise ManifestValidationError(
            f"unsupported deployment_target: {deployment_target!r}"
        )

    maturity = _require_string(data, "maturity")
    if maturity not in VALID_MATURITY:
        raise ManifestValidationError(f"unsupported maturity: {maturity!r}")

    family = _require_string(data, "family")
    parent = data.get("parent")
    if parent is not None and (not isinstance(parent, str) or not parent.strip()):
        raise ManifestValidationError("parent must be a non-empty string or null")

    native_version = data.get("native_version")
    if not isinstance(native_version, dict) or set(native_version) != {"file", "pattern"}:
        raise ManifestValidationError("native_version must contain exactly file and pattern")
    native_version_file = _require_string(native_version, "file")
    if native_version_file.startswith(("/", "\\")) or ".." in native_version_file.replace("\\", "/").split("/"):
        raise ManifestValidationError("native_version.file must be a repository-relative path")
    native_version_pattern = native_version.get("pattern")
    if isinstance(native_version_pattern, str):
        if not native_version_pattern:
            raise ManifestValidationError("native_version.pattern cannot be empty")
    elif isinstance(native_version_pattern, dict):
        if set(native_version_pattern) != {"major", "minor", "patch"} or any(
            not isinstance(value, str) or not value for value in native_version_pattern.values()
        ):
            raise ManifestValidationError(
                "native_version.pattern mapping must contain non-empty major, minor and patch regexes"
            )
    else:
        raise ManifestValidationError("native_version.pattern must be a regex string or component mapping")

    build = data.get("build")
    if not isinstance(build, str):
        raise ManifestValidationError("build must be a string")

    return ProjectManifest(
        schema_version=schema_version,
        ecosystem=ecosystem,
        name=name,
        version=version,
        role=role,
        stack=stack,
        technologies=tuple(raw_technologies),
        deployment_target=deployment_target,
        maturity=maturity,
        family=family,
        parent=parent,
        native_version_file=native_version_file,
        native_version_pattern=native_version_pattern,
        build=build,
        notes=_require_string(data, "notes"),
    )
