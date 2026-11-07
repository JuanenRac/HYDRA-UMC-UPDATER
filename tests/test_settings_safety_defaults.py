# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_settings_safety_defaults.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The defaults of the settings that gate a risky or a safety feature: what each reads with no file, with a damaged file, with a value of
the wrong type and with the value that switches it on. A feature that can do harm is off unless the file says a real true; a safety check
is on unless the file says a real false; a damaged file always takes the safe side."""
from __future__ import annotations

import json
import random

import pytest

from hydra_umc_updater import settings

# (getter, key, default with no file, value with a damaged file)
OFF_UNLESS_TRUE = [
    (settings.get_os_deploy, "os_deploy", False, False),
    (settings.get_evidence_export, "evidence_export", False, False),
    (settings.get_evidence_export_allow_plain_http, "evidence_export_allow_plain_http", False, False),
    (settings.get_image_release_require_tag, "image_release_require_tag", False, False),
    (settings.get_install_from_train, "install_from_train", False, False),
    (settings.get_require_signed_commits, "require_signed_commits", False, True),
]
ON_UNLESS_FALSE = [
    (settings.get_require_signed_packages, "require_signed_packages", True, True),
    (settings.get_recreate_venv, "recreate_venv", True, True),
]
TEXT_SETTINGS = [
    (settings.get_evidence_export_url, "evidence_export_url"),
    (settings.get_evidence_export_token_file, "evidence_export_token_file"),
    (settings.get_node_name, "node_name"),
    (settings.get_device_root, "device_root"),
    (settings.get_image_release_trusted_keys, "image_release_trusted_keys"),
    (settings.get_image_release_repo, "image_release_repo"),
    (settings.get_train_file, "train_file"),
]
WRONG_TYPES = [1, 0, "true", "false", "yes", None, [], {}, 1.0, [True]]


@pytest.fixture
def path(tmp_path, monkeypatch):
    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", target)
    monkeypatch.setattr(settings, "_LEGACY_LANG_PATH", tmp_path / "lang.json")
    return target


@pytest.mark.parametrize("getter,key,default,damaged", OFF_UNLESS_TRUE + ON_UNLESS_FALSE)
def test_the_default_with_no_file(path, getter, key, default, damaged):
    assert getter() is default


@pytest.mark.parametrize("getter,key,default,damaged", OFF_UNLESS_TRUE + ON_UNLESS_FALSE)
@pytest.mark.parametrize("content", ["not json", "[1, 2]", '"text"', "", "{", "null", "12"])
def test_a_damaged_file_takes_the_safe_side(path, getter, key, default, damaged, content):
    path.write_text(content, encoding="utf-8")
    assert getter() is damaged


@pytest.mark.parametrize("getter,key,default,damaged", OFF_UNLESS_TRUE)
def test_only_a_real_true_switches_a_risky_feature_on(path, getter, key, default, damaged):
    for value in WRONG_TYPES + [False]:
        path.write_text(json.dumps({key: value}), encoding="utf-8")
        assert getter() is default, f"{key}={value!r}"
    path.write_text(json.dumps({key: True}), encoding="utf-8")
    assert getter() is True


@pytest.mark.parametrize("getter,key,default,damaged", ON_UNLESS_FALSE)
def test_only_a_real_false_switches_a_safety_check_off(path, getter, key, default, damaged):
    for value in WRONG_TYPES + [True]:
        path.write_text(json.dumps({key: value}), encoding="utf-8")
        assert getter() is True, f"{key}={value!r}"
    path.write_text(json.dumps({key: False}), encoding="utf-8")
    assert getter() is False


@pytest.mark.parametrize("getter,key", TEXT_SETTINGS)
def test_a_text_setting_is_stripped_and_empty_or_wrong_types_are_none(path, getter, key):
    assert getter() is None
    for value in ["", "   ", "\t\n", 5, True, None, [], {}, ["a"]]:
        path.write_text(json.dumps({key: value}), encoding="utf-8")
        assert getter() is None, f"{key}={value!r}"
    path.write_text(json.dumps({key: "  value with spaces  "}), encoding="utf-8")
    assert getter() == "value with spaces"


def test_the_allowed_signers_file_must_be_a_real_file(path, tmp_path):
    assert settings.get_allowed_signers_file() is None
    real = tmp_path / "signers"
    real.write_text("x", encoding="utf-8")
    for value in ["", str(tmp_path / "missing"), str(tmp_path), 7, None, [str(real)]]:
        path.write_text(json.dumps({"allowed_signers_file": value}), encoding="utf-8")
        assert settings.get_allowed_signers_file() is None, repr(value)
    settings.save_allowed_signers_file(real)
    assert settings.get_allowed_signers_file() == str(real)


def test_the_release_channel_is_stable_unless_the_file_says_pruebas(path):
    assert settings.get_release_channel() == "stable"
    for value in ["Pruebas", "PRUEBAS", "beta", "", 1, None, ["pruebas"], "pruebas "]:
        path.write_text(json.dumps({"release_channel": value}), encoding="utf-8")
        assert settings.get_release_channel() == "stable", repr(value)
    path.write_text(json.dumps({"release_channel": "pruebas"}), encoding="utf-8")
    assert settings.get_release_channel() == "pruebas"
    path.write_text("broken", encoding="utf-8")
    assert settings.get_release_channel() == "stable"


def test_saving_a_channel_that_does_not_exist_saves_stable(path):
    settings.save_release_channel("nightly")
    assert settings.get_release_channel() == "stable"
    settings.save_release_channel("pruebas")
    assert settings.get_release_channel() == "pruebas"


def test_the_savers_round_trip_and_do_not_disturb_each_other(path):
    settings.save_os_deploy(True)
    settings.save_evidence_export(True)
    settings.save_require_signed_packages(False)
    settings.save_recreate_venv(False)
    settings.save_install_from_train(True, "train.json")
    settings.save_require_signed_commits(True)
    assert settings.get_os_deploy() is True
    assert settings.get_evidence_export() is True
    assert settings.get_require_signed_packages() is False
    assert settings.get_recreate_venv() is False
    assert settings.get_install_from_train() is True
    assert settings.get_train_file() == "train.json"
    assert settings.get_require_signed_commits() is True
    settings.save_install_from_train(False)
    assert settings.get_install_from_train() is False
    assert settings.get_train_file() == "train.json", "turning the train off keeps the file named"


def test_a_random_mix_of_values_never_raises_and_never_switches_a_risky_feature_on_by_accident(path):
    rng = random.Random(20260511)
    pool = [True, False, 0, 1, "true", "", None, [], {}, "x", 3.5]
    keys = [key for _, key, _, _ in OFF_UNLESS_TRUE + ON_UNLESS_FALSE] + [key for _, key in TEXT_SETTINGS] + ["lang", "workspace_root", "release_channel", "allowed_signers_file", "min_common_check"]
    for _ in range(200):
        document = {key: rng.choice(pool) for key in rng.sample(keys, rng.randint(0, len(keys)))}
        path.write_text(json.dumps(document), encoding="utf-8")
        for getter, key, _, _ in OFF_UNLESS_TRUE:
            assert getter() is (document.get(key) is True)
        for getter, key, _, _ in ON_UNLESS_FALSE:
            assert getter() is (document.get(key) is not False)
        for getter, _ in TEXT_SETTINGS:
            assert getter() is None or isinstance(getter(), str)
        assert settings.get_release_channel() in settings.RELEASE_CHANNELS
        assert settings.min_common_mode() in ("warn", "off")
