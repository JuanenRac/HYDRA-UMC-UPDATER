# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_edge_manifest_and_channel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Refusals of the project manifest reader and of the release resolver, with a simulated GitHub API (no network)."""
from __future__ import annotations

import copy
import json
import random
import urllib.error
from pathlib import Path

import pytest

from hydra_umc_updater.project_manifest import ManifestValidationError, parse_manifest
from hydra_umc_updater.release_channel import ReleaseError, resolve_latest

ROOT = Path(__file__).resolve().parents[1]
SHA = "c" * 40
SHA2 = "d" * 40


def good() -> dict:
    return json.loads((ROOT / "hydra-umc.project.json").read_text(encoding="utf-8"))


def refuse(mutate, fragment: str | None = None) -> None:
    data = copy.deepcopy(good())
    mutate(data)
    with pytest.raises(ManifestValidationError) as caught:
        parse_manifest(json.dumps(data))
    if fragment:
        assert fragment in str(caught.value)


def test_the_own_manifest_is_accepted() -> None:
    manifest = parse_manifest(json.dumps(good()), expected_name="HYDRA-UMC-UPDATER")
    assert manifest.name == "HYDRA-UMC-UPDATER"


def test_text_that_is_not_an_object_is_refused() -> None:
    for text in ("", "{", "[]", "7", "null", '"x"'):
        with pytest.raises(ManifestValidationError):
            parse_manifest(text)


def test_each_required_field_missing_is_named() -> None:
    required = [k for k in good() if k not in ("service", "deployment_target_note", "evidence", "hardware_bound", "depends_on", "min_common")]
    assert required
    for key in required:
        refuse(lambda d, key=key: d.pop(key), key)


def test_an_unknown_field_is_refused_so_a_typo_is_caught() -> None:
    refuse(lambda d: d.update(evidnce="x"), "unknown field")


def test_scalar_fields_are_checked() -> None:
    refuse(lambda d: d.update(evidence=""), "evidence")
    refuse(lambda d: d.update(evidence=3), "evidence")
    refuse(lambda d: d.update(schema_version="9.9"), "schema_version")
    refuse(lambda d: d.update(ecosystem="OTHER"), "ecosystem")
    refuse(lambda d: d.update(version="1.2"), "version")
    refuse(lambda d: d.update(role="wizard"), "role")
    refuse(lambda d: d.update(deployment_target="moon"), "deployment_target")
    refuse(lambda d: d.update(maturity="legendary"), "maturity")
    refuse(lambda d: d.update(parent=""), "parent")
    refuse(lambda d: d.update(parent=5), "parent")


def test_the_expected_name_must_match() -> None:
    with pytest.raises(ManifestValidationError):
        parse_manifest(json.dumps(good()), expected_name="HYDRA-UMC-OTHER")


def test_technologies_must_be_a_unique_list_of_texts() -> None:
    for bad in ([], "Python", ["a", "a"], ["a", ""], ["a", 3], None):
        refuse(lambda d, bad=bad: d.update(technologies=bad), "technologies")


def test_the_native_version_block_is_checked() -> None:
    refuse(lambda d: d.update(native_version={"file": "a"}), "native_version")
    refuse(lambda d: d.update(native_version=[]), "native_version")
    refuse(lambda d: d.update(native_version={"file": "../x", "pattern": "p"}), "repository-relative")
    refuse(lambda d: d.update(native_version={"file": "/x", "pattern": "p"}), "repository-relative")
    refuse(lambda d: d.update(native_version={"file": "a\\..\\b", "pattern": "p"}), "repository-relative")
    refuse(lambda d: d.update(native_version={"file": "a", "pattern": ""}), "pattern")
    refuse(lambda d: d.update(native_version={"file": "a", "pattern": 5}), "pattern")
    refuse(lambda d: d.update(native_version={"file": "a", "pattern": {"major": "a", "minor": "b"}}), "pattern")
    refuse(lambda d: d.update(native_version={"file": "a", "pattern": {"major": "a", "minor": "b", "patch": ""}}), "pattern")
    refuse(lambda d: d.update(native_version={"file": "a", "pattern": {"major": "a", "minor": "b", "patch": "c", "extra": "d"}}), "pattern")


def test_a_component_mapping_pattern_is_accepted() -> None:
    data = good()
    data["native_version"] = {"file": "v.h", "pattern": {"major": "A", "minor": "B", "patch": "C", "build": "D"}}
    manifest = parse_manifest(json.dumps(data))
    assert manifest.native_version_pattern == {"major": "A", "minor": "B", "patch": "C", "build": "D"}


# --------------------------------------------------------------------------- release resolver


def release(tag: str, *, draft: bool = False, prerelease: bool = False, assets=None) -> dict:
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease, "assets": assets if assets is not None else []}


def serve(releases, refs=None, tags=None):
    refs, tags = refs or {}, tags or {}

    def fetch(url: str):
        if "/releases?" in url:
            if isinstance(releases, Exception):
                raise releases
            return releases
        if "/git/ref/tags/" in url:
            answer = refs[url.rsplit("/", 1)[1]]
            if isinstance(answer, Exception):
                raise answer
            return answer
        if "/git/tags/" in url:
            return tags[url.rsplit("/", 1)[1]]
        raise AssertionError(url)

    return fetch


def commit(sha: str) -> dict:
    return {"object": {"type": "commit", "sha": sha}}


def code_of(**kwargs) -> str:
    with pytest.raises(ReleaseError) as caught:
        resolve_latest("HYDRA-UMC-X", **kwargs)
    return caught.value.code


def test_unknown_channel_and_bad_names_are_refused() -> None:
    assert code_of(channel="nightly", fetch=serve([])) == "bad_answer"
    for repo in ("", "../x", "a b", "-x", "x" * 101):
        with pytest.raises(ReleaseError):
            resolve_latest(repo, fetch=serve([]))
    with pytest.raises(ReleaseError):
        resolve_latest("HYDRA-UMC-X", fetch=serve([]), owner="bad owner")


def test_a_release_list_that_is_not_a_list_is_refused() -> None:
    for odd in ({}, "x", None, 5):
        assert code_of(fetch=serve(odd)) == "bad_answer"


def test_network_failures_are_unreachable_not_a_crash() -> None:
    for error in (urllib.error.URLError("down"), TimeoutError(), OSError("x"), ValueError("bad json")):
        assert code_of(fetch=serve(error)) == "unreachable"
    assert code_of(fetch=serve([release("v1.0.0")], {"v1.0.0": TimeoutError()})) == "unreachable"


def test_nothing_publishable_is_none() -> None:
    items = [release("v1.0.0", draft=True), release("v1.1.0", prerelease=True), release("junk"), "text", None, 4, release("v1.2.0-rc1")]
    assert code_of(fetch=serve(items)) == "none"


def test_a_suffixed_tag_not_marked_prerelease_is_never_stable() -> None:
    items = [release("v2.0.0-rc1", prerelease=False), release("v1.0.0")]
    info = resolve_latest("HYDRA-UMC-X", fetch=serve(items, {"v1.0.0": commit(SHA)}))
    assert info.tag == "v1.0.0"


def test_tags_without_the_v_and_with_four_components_are_ordered() -> None:
    items = [release("0.8.0.9"), release("0.8.1.0"), release("0.8.0.10")]
    info = resolve_latest("HYDRA-UMC-X", fetch=serve(items, {"0.8.1.0": commit(SHA)}))
    assert info.version == "0.8.1.0"


def test_the_reference_of_a_tag_must_be_usable() -> None:
    items = [release("v1.0.0")]
    for answer in ([], {}, {"object": 5}, {"object": {"type": "commit"}}, {"object": {"type": "commit", "sha": 7}}, commit("short")):
        assert code_of(fetch=serve(items, {"v1.0.0": answer})) == "bad_answer"


def test_an_annotated_tag_is_followed_and_a_chain_is_cut() -> None:
    items = [release("v1.0.0")]
    annotated = {"object": {"type": "tag", "sha": "t1"}}
    info = resolve_latest("HYDRA-UMC-X", fetch=serve(items, {"v1.0.0": annotated}, {"t1": commit(SHA2)}))
    assert info.commit == SHA2
    loop = {"object": {"type": "tag", "sha": "t1"}}
    assert code_of(fetch=serve(items, {"v1.0.0": loop}, {"t1": loop})) == "bad_answer"
    other = {"object": {"type": "tree", "sha": "t1"}}
    assert code_of(fetch=serve(items, {"v1.0.0": other})) == "bad_answer"
    assert code_of(fetch=serve(items, {"v1.0.0": annotated}, {"t1": {"object": None}})) == "bad_answer"


def test_only_well_formed_assets_are_kept() -> None:
    assets = [
        {"name": "a.zip", "browser_download_url": "https://x/a.zip"},
        {"name": 5, "browser_download_url": "https://x/b"},
        {"name": "c", "browser_download_url": None},
        "text",
    ]
    info = resolve_latest("HYDRA-UMC-X", fetch=serve([release("v1.0.0", assets=assets)], {"v1.0.0": commit(SHA)}))
    assert info.assets == {"a.zip": "https://x/a.zip"}
    none_assets = resolve_latest("HYDRA-UMC-X", fetch=serve([{"tag_name": "v1.0.0", "assets": None}], {"v1.0.0": commit(SHA)}))
    assert none_assets.assets == {}


def test_the_newest_is_chosen_whatever_the_order_with_a_fixed_seed() -> None:
    rng = random.Random(1234)
    for _ in range(40):
        versions = {(rng.randint(0, 3), rng.randint(0, 9), rng.randint(0, 9)) for _ in range(rng.randint(1, 8))}
        tags = [f"v{a}.{b}.{c}" for a, b, c in versions]
        rng.shuffle(tags)
        newest = "v{}.{}.{}".format(*max(versions))
        info = resolve_latest("HYDRA-UMC-X", fetch=serve([release(t) for t in tags], {newest: commit(SHA)}))
        assert info.tag == newest
