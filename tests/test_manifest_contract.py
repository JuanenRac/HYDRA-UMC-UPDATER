# =============================================================================
# Updater - tests/test_manifest_contract.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The updaters of the families read the same set of manifest fields.

The contract is the least every updater has to read: the fields every manifest carries, the optional ones that no updater may refuse, and the attributes
the manifest reader hands to the rest of the program. The same test is in every updater. It reads its own manifest reader, and compares it with the
readers of the other updaters when they are next to this repository (the updater of Electro Hobby 3D is read from its main branch with git, read only)."""
from __future__ import annotations

import ast
import importlib
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = next(path.name for path in (ROOT / "src").iterdir() if (path / "project_manifest.py").is_file())

#: the fields every manifest carries, in every family
REQUIRED = frozenset({
    "schema_version", "ecosystem", "name", "version", "role", "stack", "technologies", "deployment_target", "maturity",
    "family", "parent", "native_version", "build", "notes",
})
#: the optional fields every updater accepts, whatever its family
OPTIONAL = frozenset({"service", "deployment_target_note", "evidence", "hardware_bound", "min_common"})
#: the attributes of the manifest reader's result that every updater has (the native version is kept in the shape each family writes it)
ATTRIBUTES = frozenset({
    "schema_version", "ecosystem", "name", "version", "role", "stack", "technologies", "deployment_target", "maturity", "family", "parent",
    "build", "notes", "service_port", "service_health_path", "service_systemd_unit", "min_common",
})

SIBLINGS = (
    ("HYDRA-UMC-UPDATER", "hydra_umc_updater"),
    ("URTC-UPDATER", "urtc_updater"),
    ("ARMOR-UPDATER", "armor_updater"),
)


def _read_shape(source: str) -> dict[str, frozenset[str]]:
    """The fields a manifest reader asks for, read from its text: the required ones, the optional ones and the attributes of its result."""
    tree = ast.parse(source)
    shape: dict[str, frozenset[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Set) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("expected_fields", "optional_fields"):
                shape[name] = frozenset(item.value for item in node.value.elts)
        if isinstance(node, ast.ClassDef) and node.name == "ProjectManifest":
            shape["attributes"] = frozenset(item.target.id for item in node.body if isinstance(item, ast.AnnAssign))
    return shape


OWN = _read_shape((ROOT / "src" / PACKAGE / "project_manifest.py").read_text(encoding="utf-8"))


def _check(shape: dict[str, frozenset[str]]) -> None:
    assert shape["expected_fields"] == REQUIRED
    assert OPTIONAL <= shape["optional_fields"], sorted(OPTIONAL - shape["optional_fields"])
    attributes = shape["attributes"]
    assert ATTRIBUTES <= attributes, sorted(ATTRIBUTES - attributes)
    # the native version is one attribute or two (file and pattern), depending on the family
    assert "native_version" in attributes or {"native_version_file", "native_version_pattern"} <= attributes


def test_this_updater_reads_the_common_fields():
    _check(OWN)


@pytest.mark.parametrize("repo,package", SIBLINGS, ids=[name for name, _ in SIBLINGS])
def test_the_updaters_next_to_this_one_read_the_same_fields(repo, package):
    other = ROOT.parent / repo / "src" / package / "project_manifest.py"
    if not other.is_file():
        pytest.skip(f"{repo} is not next to this repository")
    _check(_read_shape(other.read_text(encoding="utf-8")))


def test_the_updater_of_electro_hobby_3d_reads_the_same_fields_from_its_main_branch():
    repo = ROOT.parent / "EH3D-UPDATER"
    if not (repo / ".git").exists():
        pytest.skip("EH3D-UPDATER is not next to this repository")
    done = subprocess.run(
        ["git", "-C", str(repo), "show", "origin/main:src/eh3d_updater/project_manifest.py"], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if done.returncode != 0:
        pytest.skip("origin/main of EH3D-UPDATER cannot be read")
    _check(_read_shape(done.stdout))


def _own_manifest() -> tuple[object, dict]:
    module = importlib.import_module(f"{PACKAGE}.project_manifest")
    return module, json.loads((ROOT / module.MANIFEST_FILE).read_text(encoding="utf-8"))


def test_the_own_manifest_of_the_repository_is_read_with_its_optional_fields():
    module, data = _own_manifest()
    parsed = module.parse_manifest(json.dumps(data))
    assert parsed.name == data["name"]
    assert parsed.min_common is None
    # every optional field that is common is accepted next to the required ones
    assert module.parse_manifest(json.dumps({**data, "evidence": "simulator", "hardware_bound": False})).name == data["name"]


def test_min_common_is_read_when_it_is_a_version_and_ignored_when_it_is_not():
    module, data = _own_manifest()
    for good in ("0.2.0", "0.8.1.6"):
        assert module.parse_manifest(json.dumps({**data, "min_common": good})).min_common == good
    for bad in ("later", "1.2", "1.2.3.4.5", 7, None, ["0.2.0"]):
        assert module.parse_manifest(json.dumps({**data, "min_common": bad})).min_common is None


def test_a_misspelled_field_is_still_refused():
    module, data = _own_manifest()
    with pytest.raises(module.ManifestValidationError):
        module.parse_manifest(json.dumps({**data, "min_comon": "0.2.0"}))
