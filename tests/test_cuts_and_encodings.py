# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_cuts_and_encodings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Files saved in another encoding or cut, and downloads cut in the middle. The network is replaced by functions, so
nothing leaves the machine."""
from __future__ import annotations

import http.client
import io
import json
import urllib.error

import pytest

from hydra_umc_updater import (
    deploy_plan,
    detect,
    evidence,
    evidence_export,
    github_client,
    package_release,
    release_channel,
    settings,
    train,
)
from hydra_umc_updater.updater_core import HYDRA_PROFILE

PRODUCT = "HYDRA-UMC-DEMO"
MANIFEST = HYDRA_PROFILE.manifest_file

DAMAGED = [
    '{"lang": "es"}'.encode("utf-16"),
    b'{"workspace_root": "C:\\\\proyectos\\\\se\xf1al"}',   # latin-1
    '{"nota": "\u65e5'.encode()[:-1],                        # cut inside a character
]


def manifest_text(name: str = PRODUCT, version: str = "1.0.0") -> str:
    return json.dumps({
        "schema_version": "1.0", "ecosystem": "HYDRA-UMC", "name": name, "version": version, "role": "service",
        "stack": "python", "technologies": ["Python"], "deployment_target": "cm5", "maturity": "functional",
        "family": "Test", "parent": None, "notes": "Test manifest.", "build": "python -m compileall src",
        "native_version": {"file": "pyproject.toml", "pattern": "(\d+)\.(\d+)\.(\d+)"},
    })


@pytest.mark.parametrize("raw", DAMAGED)
def test_a_settings_file_in_another_encoding_or_cut_never_raises(raw, isolated_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "_LEGACY_LANG_PATH", tmp_path / "lang.json")   # not the file of whoever runs it
    settings._LEGACY_LANG_PATH.write_bytes(raw)
    isolated_settings.write_bytes(raw)
    assert settings.load_settings() == {}
    assert settings.get_saved_lang() is None
    assert settings.settings_file_is_damaged() is True
    assert settings.get_require_signed_commits() is True   # fails closed
    settings.save_settings(lang="es")
    assert isolated_settings.read_bytes() == raw           # left as it was, not overwritten


def test_a_settings_file_with_a_byte_order_mark_is_read(isolated_settings):
    isolated_settings.write_bytes(b'\xef\xbb\xbf{"lang": "es", "require_signed_commits": false}')
    assert settings.load_settings()["lang"] == "es"
    assert settings.settings_file_is_damaged() is False
    assert settings.get_require_signed_commits() is False


def _folders(tmp_path):
    good = tmp_path / PRODUCT
    good.mkdir()
    (good / MANIFEST).write_bytes(b"\xef\xbb\xbf" + manifest_text().encode())
    bad = tmp_path / "HYDRA-UMC-LATIN"
    bad.mkdir()
    (bad / MANIFEST).write_bytes(b'{"notes": "se\xf1al"}')
    return good, bad


def test_one_folder_with_an_unreadable_manifest_does_not_hide_the_others(tmp_path):
    good, bad = _folders(tmp_path)
    found = detect.discover_workspace(tmp_path)
    assert [status.entry.name for status in found.projects] == [PRODUCT]
    assert len(found.errors) == 1 and bad.name in found.errors[0]
    assert deploy_plan._read_manifest(bad / MANIFEST, bad.name, HYDRA_PROFILE) is None
    assert deploy_plan._read_manifest(good / MANIFEST, PRODUCT, HYDRA_PROFILE) is not None
    assert evidence.installed_state(good)["version"] == "1.0.0"


@pytest.mark.parametrize("raw", [b"[1, 2]", b'"text"', b"\xff\xfe{", b"{ cut"])
def test_the_installed_state_of_a_damaged_manifest_is_unknown(tmp_path, raw):
    (tmp_path / MANIFEST).write_bytes(raw)
    assert evidence.installed_state(tmp_path)["version"] is None


def test_a_train_or_a_token_file_in_another_encoding_is_a_message(tmp_path):
    path = tmp_path / "train.json"
    path.write_bytes(b"\xff\xfe{\x00}\x00")
    with pytest.raises(train.TrainError):
        train.load_train(path)
    assert evidence_export.read_token(str(path)) is None
    token = tmp_path / "token"
    token.write_bytes(b"\xef\xbb\xbfsecret-value\r\n")
    assert evidence_export.read_token(str(token)) == "secret-value"   # the mark never travels in a header


class CutAnswer(io.BytesIO):
    headers = None

    def read(self, *args):
        raise http.client.IncompleteRead(b"{", 100)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_a_download_cut_in_the_middle_is_asked_again():
    answers = [CutAnswer(), CutAnswer(), io.BytesIO(b"whole")]
    body = github_client._urlopen_with_retries(
        object(), timeout=1, max_attempts=3, opener=lambda request, timeout: answers.pop(0), sleep=lambda s: None)
    assert body == b"whole"


def _cut(monkeypatch, failing: str):
    def opener(request, *args, **kwargs):
        if failing in request.full_url:
            raise http.client.IncompleteRead(b"{", 100)
        raise urllib.error.HTTPError(request.full_url, 404, "not found", None, None)

    original = github_client._urlopen_with_retries
    monkeypatch.setattr(github_client, "_urlopen_with_retries",
                        lambda request, **kw: original(request, opener=opener, sleep=lambda s: None, **kw))


def test_a_cut_repository_listing_is_a_message(monkeypatch):
    _cut(monkeypatch, "/users/")
    with pytest.raises(RuntimeError, match="IncompleteRead"):
        github_client.discover_remote_projects("someone", token="")


def test_a_cut_manifest_does_not_end_the_discovery_of_the_others(monkeypatch):
    listing = json.dumps([{"name": "HYDRA-UMC-CUT"}, {"name": PRODUCT}]).encode()

    def answer(request, **kwargs):
        if "/users/" in request.full_url:
            return listing
        if "HYDRA-UMC-CUT" in request.full_url:
            raise http.client.IncompleteRead(b"{", 100)
        return manifest_text().encode()

    monkeypatch.setattr(github_client, "_urlopen_with_retries", answer)
    found = github_client.discover_remote_projects("someone", token="")
    assert [status.entry.name for status in found.projects] == [PRODUCT]
    assert len(found.errors) == 1 and "HYDRA-UMC-CUT" in found.errors[0]


def test_a_cut_release_lookup_is_unreachable():
    def fetch(url):
        raise http.client.IncompleteRead(b"[", 100)

    with pytest.raises(release_channel.ReleaseError) as stop:
        release_channel.resolve_latest(PRODUCT, fetch=fetch)
    assert stop.value.code == "unreachable"


def test_a_cut_package_download_is_a_message(tmp_path):
    name = f"{PRODUCT}-1.0.0.tgz"
    info = release_channel.ReleaseInfo(
        repo=PRODUCT, tag="v1.0.0", version="1.0.0", prerelease=False, plain=True, commit="0" * 40,
        assets={name: f"https://github.com/JuanenRac/{PRODUCT}/releases/download/v1.0.0/{name}"})

    def download(url, destination, limit):
        raise http.client.IncompleteRead(b"x", 100)

    with pytest.raises(package_release.PackageError) as stop:
        package_release.fetch_release_package(info, tmp_path, download=download)
    assert stop.value.code == "download_failed"
