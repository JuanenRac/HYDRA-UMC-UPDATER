# =============================================================================
# HYDRA-UMC-UPDATER - Universal project manifest tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json

import pytest

from hydra_umc_updater.project_manifest import ManifestValidationError, parse_manifest


def valid_manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "ecosystem": "HYDRA-UMC",
        "name": "HYDRA-UMC-EXAMPLE",
        "version": "1.2.3",
        "role": "service",
        "stack": "python",
        "technologies": ["Python", "systemd"],
        "deployment_target": "cm5",
        "maturity": "functional",
        "family": "Example family",
        "parent": None,
        "native_version": {
            "file": "pyproject.toml",
            "pattern": "^version\\s*=\\s*\"(\\d+)\\.(\\d+)\\.(\\d+)\"",
        },
        "build": "python -m build",
        "notes": "A test-only manifest.",
    }


def test_parses_a_complete_v1_manifest():
    manifest = parse_manifest(json.dumps(valid_manifest()), expected_name="HYDRA-UMC-EXAMPLE")
    assert manifest.version == "1.2.3"
    assert manifest.technologies == ("Python", "systemd")


def test_rejects_an_identity_mismatch():
    with pytest.raises(ManifestValidationError, match="does not match"):
        parse_manifest(json.dumps(valid_manifest()), expected_name="HYDRA-UMC-OTHER")


def test_rejects_an_unsupported_maturity():
    data = valid_manifest()
    data["maturity"] = "almost-production"
    with pytest.raises(ManifestValidationError, match="unsupported maturity"):
        parse_manifest(json.dumps(data))


def test_rejects_unknown_fields_to_prevent_silent_dashboard_drift():
    data = valid_manifest()
    data["deployment"] = "cm5"
    with pytest.raises(ManifestValidationError, match="unknown field"):
        parse_manifest(json.dumps(data))
