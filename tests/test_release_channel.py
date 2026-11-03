# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_release_channel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The latest stable release is what gets installed, never the head of the branch. The GitHub API is simulated: no network."""
from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from hydra_umc_updater import install, release_channel, settings
from hydra_umc_updater.install import resolve_release_pin as real_resolve_release_pin
from hydra_umc_updater.install import install_or_update
from hydra_umc_updater.release_channel import ReleaseError, resolve_latest

SHA = "a" * 40
SHA2 = "b" * 40


def release(tag: str, *, draft: bool = False, prerelease: bool = False) -> dict:
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease, "assets": []}


def api(releases, refs: dict[str, dict] | None = None, tags: dict[str, dict] | None = None):
    """A fetch function that serves made-up answers; every other address is a failure."""
    refs = refs or {}
    tags = tags or {}

    def fetch(url: str):
        if "/releases?" in url:
            if isinstance(releases, Exception):
                raise releases
            return releases
        if "/git/ref/tags/" in url:
            return refs[url.rsplit("/", 1)[1]]
        if "/git/tags/" in url:
            return tags[url.rsplit("/", 1)[1]]
        raise AssertionError(url)

    return fetch


def lightweight(sha: str) -> dict:
    return {"object": {"type": "commit", "sha": sha}}


def test_stable_takes_the_highest_published_release_and_skips_drafts_and_prereleases() -> None:
    releases = [
        release("v0.9.0", draft=True),
        release("v0.8.2.0", prerelease=True),
        release("v0.8.1.0"),
        release("v0.8.0.9"),
        release("not-a-version"),
    ]
    info = resolve_latest("HYDRA-UMC-X", fetch=api(releases, {"v0.8.1.0": lightweight(SHA)}))
    assert (info.tag, info.version, info.commit, info.prerelease, info.plain) == ("v0.8.1.0", "0.8.1.0", SHA, False, True)


def test_the_order_is_by_version_not_by_position_in_the_list() -> None:
    releases = [release("v0.2.0"), release("v0.10.0"), release("v0.9.5")]
    info = resolve_latest("HYDRA-UMC-X", fetch=api(releases, {"v0.10.0": lightweight(SHA)}))
    assert info.version == "0.10.0"


def test_the_testing_channel_also_takes_prereleases_and_a_plain_version_beats_its_candidates() -> None:
    releases = [release("v0.3.0-rc1", prerelease=True), release("v0.2.0")]
    refs = {"v0.3.0-rc1": lightweight(SHA2), "v0.2.0": lightweight(SHA)}
    assert resolve_latest("R", "pruebas", fetch=api(releases, refs)).tag == "v0.3.0-rc1"
    assert resolve_latest("R", "stable", fetch=api(releases, refs)).tag == "v0.2.0"
    both = [release("v0.3.0-rc1", prerelease=True), release("v0.3.0")]
    refs["v0.3.0"] = lightweight(SHA)
    assert resolve_latest("R", "pruebas", fetch=api(both, refs)).tag == "v0.3.0"


def test_an_annotated_tag_is_followed_to_its_commit() -> None:
    refs = {"v1.0.0": {"object": {"type": "tag", "sha": "c" * 40}}}
    tags = {"c" * 40: {"object": {"type": "commit", "sha": SHA}}}
    assert resolve_latest("R", fetch=api([release("v1.0.0")], refs, tags)).commit == SHA


def test_assets_are_listed_by_name() -> None:
    item = release("v1.0.0")
    item["assets"] = [{"name": "R-1.0.0.tgz", "browser_download_url": "https://github.com/x/y"}, {"name": 3}]
    assert resolve_latest("R", fetch=api([item], {"v1.0.0": lightweight(SHA)})).assets == {"R-1.0.0.tgz": "https://github.com/x/y"}


@pytest.mark.parametrize(
    ("releases", "code"),
    [
        ([], "none"),
        ([release("v1.0.0", draft=True), release("v1.1.0", prerelease=True)], "none"),
        ({"message": "Not Found"}, "bad_answer"),
        (urllib.error.URLError("offline"), "unreachable"),
        (TimeoutError("slow"), "unreachable"),
    ],
)
def test_no_usable_release_is_a_clear_failure(releases, code: str) -> None:
    with pytest.raises(ReleaseError) as caught:
        resolve_latest("R", fetch=api(releases))
    assert caught.value.code == code


def test_a_tag_that_does_not_lead_to_a_commit_is_refused() -> None:
    with pytest.raises(ReleaseError) as caught:
        resolve_latest("R", fetch=api([release("v1.0.0")], {"v1.0.0": {"object": {"type": "blob", "sha": SHA}}}))
    assert caught.value.code == "bad_answer"
    with pytest.raises(ReleaseError):
        resolve_latest("R", fetch=api([release("v1.0.0")], {"v1.0.0": {"object": {"type": "commit", "sha": "not-a-sha"}}}))


def test_names_that_could_change_the_address_are_refused() -> None:
    for name in ("../x", "a/b", "", "a b"):
        with pytest.raises(ReleaseError):
            resolve_latest(name, fetch=api([]))
    with pytest.raises(ReleaseError):
        resolve_latest("R", "head", fetch=api([]))


def test_the_channel_is_stable_unless_the_settings_say_pruebas(isolated_settings: Path) -> None:
    assert settings.get_release_channel() == "stable"
    settings.save_release_channel("pruebas")
    assert settings.get_release_channel() == "pruebas"
    settings.save_release_channel("head")
    assert settings.get_release_channel() == "stable"
    isolated_settings.write_text("{not json", encoding="utf-8")
    assert settings.get_release_channel() == "stable"


# ---- the installation uses the release, with real git repositories and a simulated API ---------------------------------------------------------------------------------------


@pytest.fixture
def releases_of(monkeypatch: pytest.MonkeyPatch):
    """Point the real resolver at a simulated API: {name: (releases, {tag: commit})}."""
    monkeypatch.setattr(install, "resolve_release_pin", real_resolve_release_pin)
    table: dict[str, tuple[object, dict[str, str]]] = {}

    def fetch(url: str):
        name = url.split("/repos/JuanenRac/", 1)[1].split("/", 1)[0]
        releases, commits = table[name]
        if isinstance(releases, Exception):
            raise releases
        if "/releases?" in url:
            return releases
        return lightweight(commits[url.rsplit("/", 1)[1]])

    monkeypatch.setattr(release_channel, "fetch_json", fetch)
    return table


def version_of(path: Path) -> str:
    return json.loads((path / "hydra-umc.project.json").read_text(encoding="utf-8"))["version"]


def test_a_first_install_gets_the_release_and_not_the_head(world, releases_of) -> None:
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0", "0.2.0", "0.3.0")
    releases_of["HYDRA-UMC-DEMO"] = ([release("v0.2.0"), release("v0.1.0")], {"v0.2.0": repo.commits["0.2.0"], "v0.1.0": repo.commits["0.1.0"]})
    results = install_or_update(world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"], world.workspace)
    assert all(r.ok for r in results), [r.message for r in results]
    assert version_of(world.workspace / "HYDRA-UMC-DEMO") == "0.2.0"


def test_an_update_moves_to_the_latest_release_and_not_to_the_head(world, releases_of) -> None:
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0")
    entry = world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"]
    releases_of["HYDRA-UMC-DEMO"] = ([release("v0.1.0")], {"v0.1.0": repo.commits["0.1.0"]})
    assert all(r.ok for r in install_or_update(entry, world.workspace))
    repo.publish("0.2.0")
    repo.publish("0.3.0")
    releases_of["HYDRA-UMC-DEMO"] = ([release("v0.2.0"), release("v0.1.0")], {"v0.2.0": repo.commits["0.2.0"], "v0.1.0": repo.commits["0.1.0"]})
    results = install_or_update(entry, world.workspace)
    assert all(r.ok for r in results), [r.message for r in results]
    assert version_of(world.workspace / "HYDRA-UMC-DEMO") == "0.2.0"


def test_the_testing_channel_installs_the_prerelease(world, releases_of) -> None:
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0", "0.2.0")
    releases_of["HYDRA-UMC-DEMO"] = (
        [release("v0.2.0-rc1", prerelease=True), release("v0.1.0")],
        {"v0.2.0-rc1": repo.commits["0.2.0"], "v0.1.0": repo.commits["0.1.0"]},
    )
    settings.save_release_channel("pruebas")
    results = install_or_update(world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"], world.workspace)
    assert all(r.ok for r in results), [r.message for r in results]
    assert version_of(world.workspace / "HYDRA-UMC-DEMO") == "0.2.0"


@pytest.mark.parametrize("answer", [[], [release("v0.3.0", draft=True)], [release("v0.3.0-rc1", prerelease=True)], urllib.error.URLError("offline")])
def test_without_a_release_or_without_network_nothing_is_installed_and_the_head_is_not_used(world, releases_of, answer) -> None:
    world.make("HYDRA-UMC-DEMO", "0.1.0", "0.2.0")
    releases_of["HYDRA-UMC-DEMO"] = (answer, {})
    results = install_or_update(world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"], world.workspace)
    assert [r.ok for r in results] == [False]
    assert "nothing was installed" in results[0].message
    assert not (world.workspace / "HYDRA-UMC-DEMO").exists()


def test_an_installed_project_is_left_alone_when_the_release_cannot_be_found(world, releases_of) -> None:
    repo = world.make("HYDRA-UMC-DEMO", "0.1.0")
    entry = world.entries("HYDRA-UMC-DEMO")["HYDRA-UMC-DEMO"]
    releases_of["HYDRA-UMC-DEMO"] = ([release("v0.1.0")], {"v0.1.0": repo.commits["0.1.0"]})
    assert all(r.ok for r in install_or_update(entry, world.workspace))
    repo.publish("0.2.0")
    releases_of["HYDRA-UMC-DEMO"] = (urllib.error.URLError("offline"), {})
    assert not install_or_update(entry, world.workspace)[0].ok
    assert version_of(world.workspace / "HYDRA-UMC-DEMO") == "0.1.0"
