# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_settings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real, file-backed persistence tests for settings.py - the shared
# ~/.hydra_umc_updater_settings.json a real user's remembered workspace
# root and language both now live in. Real temp-directory files, no
# mocking of the filesystem itself.
# =============================================================================
from __future__ import annotations

import json

import pytest

from hydra_umc_updater import settings


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    fake_path = tmp_path / ".hydra_umc_updater_settings.json"
    fake_legacy_path = tmp_path / ".hydra_umc_updater_lang.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", fake_path)
    monkeypatch.setattr(settings, "_LEGACY_LANG_PATH", fake_legacy_path)
    return fake_path


def test_load_settings_returns_empty_dict_when_no_file_exists(isolated_settings):
    assert settings.load_settings() == {}


def test_load_settings_returns_empty_dict_for_corrupt_json(isolated_settings):
    isolated_settings.write_text("not json at all", encoding="utf-8")
    assert settings.load_settings() == {}


def test_load_settings_returns_empty_dict_for_a_non_object_top_level(isolated_settings):
    isolated_settings.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert settings.load_settings() == {}


def test_save_settings_merges_instead_of_overwriting(isolated_settings):
    settings.save_settings(lang="es")
    settings.save_settings(workspace_root="/some/real/path")
    saved = settings.load_settings()
    assert saved["lang"] == "es"
    assert saved["workspace_root"] == "/some/real/path"


def test_save_settings_updates_an_existing_key_without_disturbing_others(isolated_settings):
    settings.save_settings(lang="es", workspace_root="/a")
    settings.save_settings(lang="de")
    saved = settings.load_settings()
    assert saved == {"lang": "de", "workspace_root": "/a"}


def test_get_saved_workspace_root_is_none_when_never_saved(isolated_settings):
    assert settings.get_saved_workspace_root() is None


def test_get_saved_workspace_root_round_trips_for_a_real_existing_directory(isolated_settings, tmp_path):
    real_dir = tmp_path / "workspace"
    real_dir.mkdir()
    settings.save_workspace_root(real_dir)
    assert settings.get_saved_workspace_root() == real_dir


def test_get_saved_workspace_root_refuses_a_path_that_no_longer_exists(isolated_settings, tmp_path):
    # Real fail-safe: a saved path pointing at a since-deleted/renamed/
    # unmounted directory must never be silently handed back as if it
    # were still valid - every real project inside it would look "not
    # installed" against a workspace that doesn't even exist.
    gone_dir = tmp_path / "deleted-later"
    gone_dir.mkdir()
    settings.save_workspace_root(gone_dir)
    gone_dir.rmdir()
    assert settings.get_saved_workspace_root() is None


def test_get_saved_workspace_root_refuses_a_path_that_is_a_file_not_a_directory(isolated_settings, tmp_path):
    a_file = tmp_path / "not-a-directory.txt"
    a_file.write_text("x", encoding="utf-8")
    settings.save_workspace_root(a_file)
    assert settings.get_saved_workspace_root() is None


def test_get_saved_lang_prefers_the_new_shared_file_over_the_legacy_one(isolated_settings):
    settings._LEGACY_LANG_PATH.write_text(json.dumps({"lang": "it"}), encoding="utf-8")
    settings.save_lang("ja")
    assert settings.get_saved_lang() == "ja"


def test_get_saved_lang_falls_back_to_the_real_legacy_file_when_the_new_one_has_no_lang(isolated_settings, tmp_path):
    settings._LEGACY_LANG_PATH.write_text(json.dumps({"lang": "fr"}), encoding="utf-8")
    assert settings.get_saved_lang() == "fr"


def test_get_saved_lang_is_none_when_neither_file_exists(isolated_settings):
    assert settings.get_saved_lang() is None


def test_workspace_root_and_lang_persist_independently_side_by_side(isolated_settings, tmp_path):
    real_dir = tmp_path / "ecosystem"
    real_dir.mkdir()
    settings.save_lang("de")
    settings.save_workspace_root(real_dir)
    assert settings.get_saved_lang() == "de"
    assert settings.get_saved_workspace_root() == real_dir
