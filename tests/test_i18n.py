# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_i18n.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real tests for i18n.py - the GUI's own 7-language translation table and
# the real (file-backed) preference persistence gui.py's language
# Combobox depends on.
# =============================================================================
from __future__ import annotations

import json

import pytest

from hydra_umc_updater import i18n


def test_every_language_has_exactly_the_same_keys_as_english():
    en_keys = set(i18n.TRANSLATIONS["en"].keys())
    assert len(en_keys) > 0
    for lang, table in i18n.TRANSLATIONS.items():
        assert set(table.keys()) == en_keys, f"{lang} has a different key set than en"


def test_languages_list_matches_translations_dict():
    codes = {code for code, _label in i18n.LANGUAGES}
    assert codes == set(i18n.TRANSLATIONS.keys())


def test_t_substitutes_real_placeholders():
    text = i18n.t("en", "msg_already_installed", name="HYDRA-UMC-SERVER", path="/repos/HYDRA-UMC-SERVER")
    assert "HYDRA-UMC-SERVER" in text
    assert "/repos/HYDRA-UMC-SERVER" in text


def test_t_falls_back_to_english_for_an_unknown_language():
    assert i18n.t("xx", "refresh_button") == i18n.TRANSLATIONS["en"]["refresh_button"]


def test_t_falls_back_to_the_key_itself_for_an_unknown_key():
    assert i18n.t("en", "this_key_does_not_exist") == "this_key_does_not_exist"


def test_t_does_not_crash_on_a_missing_placeholder_value():
    # A real template referencing {name} with no name= kwarg supplied -
    # must return the raw template rather than raising, the same
    # defensive spirit as every other real fallback in this module.
    result = i18n.t("en", "msg_already_installed")
    assert "{name}" in result


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    fake_path = tmp_path / ".hydra_umc_updater_lang.json"
    monkeypatch.setattr(i18n, "_CONFIG_PATH", fake_path)
    return fake_path


def test_save_and_load_lang_preference_round_trips_for_real(isolated_config):
    assert i18n._load_saved_lang() is None
    i18n.save_lang_preference("ja")
    assert isolated_config.exists()
    assert json.loads(isolated_config.read_text(encoding="utf-8")) == {"lang": "ja"}
    assert i18n._load_saved_lang() == "ja"


def test_load_saved_lang_ignores_an_unsupported_language_code(isolated_config):
    isolated_config.write_text(json.dumps({"lang": "klingon"}), encoding="utf-8")
    assert i18n._load_saved_lang() is None


def test_load_saved_lang_ignores_a_corrupt_file(isolated_config):
    isolated_config.write_text("not json at all", encoding="utf-8")
    assert i18n._load_saved_lang() is None


def test_resolve_initial_lang_prefers_a_real_saved_preference(isolated_config, monkeypatch):
    i18n.save_lang_preference("de")
    # Even if the OS locale would resolve to something else, a real saved
    # preference on this machine must win - that's the whole point of
    # persisting it in the first place.
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("fr_FR", "UTF-8"))
    assert i18n.resolve_initial_lang() == "de"


def test_resolve_initial_lang_falls_back_to_locale_when_nothing_saved(isolated_config, monkeypatch):
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("it_IT", "UTF-8"))
    assert i18n.resolve_initial_lang() == "it"


def test_resolve_initial_lang_falls_back_to_english_for_an_unsupported_locale(isolated_config, monkeypatch):
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("ko_KR", "UTF-8"))
    assert i18n.resolve_initial_lang() == "en"
