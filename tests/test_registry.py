# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Tests for generic runtime entries; no fixed ecosystem project list."""

from hydra_umc_updater.project_manifest import parse_manifest
from hydra_umc_updater.registry import entry_from_manifest, github_native_version_url, github_raw_url


def test_runtime_entry_uses_repository_owned_native_version_data():
    manifest = parse_manifest(
        r'''{
          "schema_version": "1.0", "ecosystem": "HYDRA-UMC",
          "name": "HYDRA-UMC-EXAMPLE", "version": "1.2.3",
          "role": "service", "stack": "python", "technologies": ["Python"],
          "deployment_target": "cm5", "maturity": "functional",
          "family": "Examples", "parent": null,
          "native_version": {"file": "pyproject.toml", "pattern": "version = \"(\\d+)\\.(\\d+)\\.(\\d+)\""},
          "build": "python -m example", "notes": "Example."
        }''',
        expected_name="HYDRA-UMC-EXAMPLE",
    )
    entry = entry_from_manifest(manifest)

    assert entry.version_file == "pyproject.toml"
    assert entry.pattern == 'version = "(\\d+)\\.(\\d+)\\.(\\d+)"'
    assert github_raw_url(entry).endswith("/HYDRA-UMC-EXAMPLE/main/hydra-umc.project.json")
    assert github_native_version_url(entry).endswith("/HYDRA-UMC-EXAMPLE/main/pyproject.toml")
