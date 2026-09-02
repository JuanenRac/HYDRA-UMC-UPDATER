# =============================================================================
# HYDRA-UMC-UPDATER - Universal project manifest tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hydra_umc_updater.project_manifest import ManifestValidationError, parse_manifest


def test_package_version_mirror_matches_pyproject_version():
    """The runtime --version mirror must not drift from the package source."""
    repository = Path(__file__).resolve().parents[1]
    pyproject = (repository / "pyproject.toml").read_text(encoding="utf-8")
    package_init = (repository / "src" / "hydra_umc_updater" / "__init__.py").read_text(encoding="utf-8")

    package_version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    runtime_version = re.search(r'^__version__\s*=\s*"([^"]+)"', package_init, re.MULTILINE)

    assert package_version is not None, "pyproject.toml must declare [project].version"
    assert runtime_version is not None, "__init__.py must define __version__"
    assert runtime_version.group(1) == package_version.group(1)


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


def test_service_is_absent_by_default():
    manifest = parse_manifest(json.dumps(valid_manifest()))
    assert manifest.service_port is None
    assert manifest.service_health_path is None
    assert manifest.service_systemd_unit is None


def test_parses_a_real_service_port_and_health_path():
    data = valid_manifest()
    data["service"] = {"port": 3000, "health_path": "/api/system/metrics"}
    manifest = parse_manifest(json.dumps(data))
    assert manifest.service_port == 3000
    assert manifest.service_health_path == "/api/system/metrics"


def test_service_health_path_is_optional_tcp_only_check():
    data = valid_manifest()
    data["service"] = {"port": 1883}
    manifest = parse_manifest(json.dumps(data))
    assert manifest.service_port == 1883
    assert manifest.service_health_path is None


def test_rejects_a_service_port_out_of_range():
    data = valid_manifest()
    data["service"] = {"port": 70000}
    with pytest.raises(ManifestValidationError, match="service.port"):
        parse_manifest(json.dumps(data))


def test_rejects_a_service_health_path_without_a_leading_slash():
    data = valid_manifest()
    data["service"] = {"port": 3000, "health_path": "api/system/metrics"}
    with pytest.raises(ManifestValidationError, match="service.health_path"):
        parse_manifest(json.dumps(data))


def test_rejects_an_unknown_field_inside_service():
    data = valid_manifest()
    data["service"] = {"port": 3000, "protocol": "http"}
    with pytest.raises(ManifestValidationError, match="unknown field.*service"):
        parse_manifest(json.dumps(data))


def test_parses_a_real_service_systemd_unit():
    data = valid_manifest()
    data["service"] = {
        "port": 3000,
        "health_path": "/api/system/metrics",
        "systemd_unit": "hydra-umc-server.service",
    }
    manifest = parse_manifest(json.dumps(data))
    assert manifest.service_systemd_unit == "hydra-umc-server.service"


def test_service_systemd_unit_is_optional():
    data = valid_manifest()
    data["service"] = {"port": 3000}
    manifest = parse_manifest(json.dumps(data))
    assert manifest.service_systemd_unit is None


def test_rejects_a_service_systemd_unit_without_the_service_suffix():
    data = valid_manifest()
    data["service"] = {"port": 3000, "systemd_unit": "hydra-umc-server"}
    with pytest.raises(ManifestValidationError, match="service.systemd_unit"):
        parse_manifest(json.dumps(data))


def test_parses_a_systemd_unit_alone_with_no_port():
    """A background worker service that never listens on a network port -
    e.g. HYDRA-UMC-COGNITIVE-NODE - still needs to declare which systemd
    unit it runs as without being forced to also declare a fake port."""
    data = valid_manifest()
    data["service"] = {"systemd_unit": "hydra-umc-cognitive-node.service"}
    manifest = parse_manifest(json.dumps(data))
    assert manifest.service_port is None
    assert manifest.service_health_path is None
    assert manifest.service_systemd_unit == "hydra-umc-cognitive-node.service"


def test_rejects_an_empty_service_object():
    data = valid_manifest()
    data["service"] = {}
    with pytest.raises(ManifestValidationError, match="service must declare at least one"):
        parse_manifest(json.dumps(data))


def test_rejects_a_service_health_path_without_a_port():
    data = valid_manifest()
    data["service"] = {"health_path": "/healthz", "systemd_unit": "hydra-umc-example.service"}
    with pytest.raises(ManifestValidationError, match="service.health_path requires service.port"):
        parse_manifest(json.dumps(data))
