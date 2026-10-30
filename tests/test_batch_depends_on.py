# =============================================================================
# HYDRA-UMC-UPDATER - Order of a batch by the depends_on of the manifests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json

import pytest

from hydra_umc_updater.install import batch_order_key, format_batch_list, order_batch
from hydra_umc_updater.project_manifest import ManifestValidationError, parse_manifest
from hydra_umc_updater.registry import entry_from_manifest
from test_project_manifest import valid_manifest


def test_without_dependencies_the_order_is_the_plain_one():
    names = ["HYDRA-UMC-UPDATER", "HYDRA-UMC-STUDIO", "HYDRA-UMC-SDK", "HYDRA-UMC-AAA"]
    assert order_batch(names) == sorted(names, key=batch_order_key)
    assert order_batch(names, {}) == sorted(names, key=batch_order_key)


def test_a_project_goes_after_the_ones_it_depends_on():
    names = ["HYDRA-UMC-AAA", "HYDRA-UMC-BBB", "HYDRA-UMC-CCC", "HYDRA-UMC-SDK"]
    result = order_batch(names, {"HYDRA-UMC-AAA": ["HYDRA-UMC-CCC"], "HYDRA-UMC-CCC": ["HYDRA-UMC-BBB"]})
    assert result == ["HYDRA-UMC-SDK", "HYDRA-UMC-BBB", "HYDRA-UMC-CCC", "HYDRA-UMC-AAA"]


def test_a_dependency_outside_the_batch_is_ignored():
    names = ["HYDRA-UMC-AAA", "HYDRA-UMC-BBB"]
    assert order_batch(names, {"HYDRA-UMC-AAA": ["HYDRA-UMC-OS"]}) == names


def test_a_cycle_is_still_ordered_and_loses_no_project():
    names = ["HYDRA-UMC-AAA", "HYDRA-UMC-BBB", "HYDRA-UMC-CCC"]
    result = order_batch(names, {"HYDRA-UMC-AAA": ["HYDRA-UMC-BBB"], "HYDRA-UMC-BBB": ["HYDRA-UMC-AAA"]})
    assert sorted(result) == names
    assert len(result) == len(set(result))


def test_the_updater_stays_last_unless_something_depends_on_it():
    names = ["HYDRA-UMC-UPDATER", "HYDRA-UMC-AAA", "HYDRA-UMC-BBB"]
    assert order_batch(names)[-1] == "HYDRA-UMC-UPDATER"
    assert order_batch(names, {"HYDRA-UMC-AAA": ["HYDRA-UMC-UPDATER"]}).index("HYDRA-UMC-UPDATER") < order_batch(
        names, {"HYDRA-UMC-AAA": ["HYDRA-UMC-UPDATER"]}
    ).index("HYDRA-UMC-AAA")


def test_the_confirmation_list_follows_the_same_order():
    text = format_batch_list(["HYDRA-UMC-AAA", "HYDRA-UMC-BBB"], depends_on={"HYDRA-UMC-AAA": ["HYDRA-UMC-BBB"]})
    assert text.splitlines() == ["1. HYDRA-UMC-BBB", "2. HYDRA-UMC-AAA"]


def test_the_manifest_depends_on_reaches_the_entry():
    data = valid_manifest()
    data["depends_on"] = ["HYDRA-UMC-SDK", "HYDRA-UMC-OS"]
    manifest = parse_manifest(json.dumps(data))
    assert manifest.depends_on == ("HYDRA-UMC-SDK", "HYDRA-UMC-OS")
    assert entry_from_manifest(manifest).depends_on == ("HYDRA-UMC-SDK", "HYDRA-UMC-OS")
    assert parse_manifest(json.dumps(valid_manifest())).depends_on == ()


@pytest.mark.parametrize("bad", [["HYDRA-UMC-OS", "HYDRA-UMC-OS"], ["os"], [5], "HYDRA-UMC-OS", ["HYDRA-UMC-EXAMPLE"]])
def test_a_wrong_depends_on_is_refused(bad):
    data = valid_manifest()
    data["depends_on"] = bad
    with pytest.raises(ManifestValidationError):
        parse_manifest(json.dumps(data))
