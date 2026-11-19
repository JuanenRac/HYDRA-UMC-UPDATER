# =============================================================================
# HYDRA-UMC-UPDATER - Signature of the update manifest: update_manifest.py and `manifest verify`
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The conformance vectors of the SDK (a copy in tests/fixtures), the switch `require_asymmetric_signature` (off by default, on when the settings file is
damaged) and the command, in every language. The keys are test seeds written in the vectors, never a real key."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hydra_umc_updater import i18n, main, settings, update_manifest

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "manifest-signing-vectors.json").read_text(encoding="utf-8"))
NOW = "2030-03-01T00:00:00Z"
GOOD = next(c for c in VECTORS["cases"] if c["name"] == "a good signature passes with the switch off")["manifest"]
LEGACY = next(c for c in VECTORS["cases"] if c["name"] == "a legacy manifest passes with the switch off")["manifest"]


def moment(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@pytest.fixture()
def keys_file(tmp_path: Path) -> Path:
    path = tmp_path / "keys.json"
    path.write_text(json.dumps(VECTORS["keys"]), encoding="utf-8")
    return path


def write(tmp_path: Path, manifest: dict, name: str = "manifest.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def call(args: list[str]) -> int:
    parsed = main.build_parser().parse_args(["manifest", "verify", *args])
    return parsed.func(parsed)


def run(args: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path, saved: dict | None = None, damaged: bool = False) -> int:
    settings_path = tmp_path / "settings.json"
    if damaged:
        settings_path.write_text("[not an object", encoding="utf-8")
    elif saved is not None:
        settings_path.write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(settings, "SETTINGS_PATH", settings_path)
    for name in ("HYDRA_UMC_UPDATER_REQUIRE_ASYMMETRIC_SIGNATURE", "HYDRA_UMC_UPDATER_MANIFEST_TRUSTED_KEYS"):
        monkeypatch.delenv(name, raising=False)
    return call(args)


def test_every_conformance_vector_gives_the_verdict_of_the_sdk() -> None:
    keys = update_manifest.keys_from_json(json.dumps(VECTORS["keys"]))
    assert len(VECTORS["cases"]) >= 18
    for case in VECTORS["cases"]:
        verdict = update_manifest.verify_manifest(case["manifest"], keys, moment(case["now"]), require_asymmetric_signature=case["require_asymmetric_signature"])
        assert (verdict.accepted, verdict.code) == (case["accepted"], case["code"]), case["name"]


def test_the_switch_is_off_by_default_and_on_for_a_damaged_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "none.json")
    assert settings.get_require_asymmetric_signature() is False
    settings.save_require_asymmetric_signature(True)
    assert settings.get_require_asymmetric_signature() is True
    damaged = tmp_path / "damaged.json"
    damaged.write_text("[", encoding="utf-8")
    monkeypatch.setattr(settings, "SETTINGS_PATH", damaged)
    assert settings.get_require_asymmetric_signature() is True


def test_a_good_signature_passes_whatever_the_switch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path) -> None:
    manifest = write(tmp_path, GOOD)
    assert run([str(manifest), "--trusted-keys", str(keys_file), "--now", NOW], monkeypatch, tmp_path) == 0
    assert run([str(manifest), "--trusted-keys", str(keys_file), "--now", NOW, "--require-asymmetric-signature"], monkeypatch, tmp_path) == 0


def test_a_bad_signature_is_refused_even_with_the_switch_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tampered = write(tmp_path, dict(GOOD, sha256="f" * 64))
    assert run([str(tampered), "--trusted-keys", str(keys_file), "--now", NOW, "--lang", "en"], monkeypatch, tmp_path) == 1
    assert "does not verify" in capsys.readouterr().err


def test_a_rotated_out_key_is_refused_after_its_grace_period(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path) -> None:
    old = next(c for c in VECTORS["cases"] if c["name"] == "the retired key is refused after its grace period")["manifest"]
    manifest = write(tmp_path, old)
    assert run([str(manifest), "--trusted-keys", str(keys_file), "--now", "2030-06-01T00:00:00Z"], monkeypatch, tmp_path) == 1
    assert run([str(manifest), "--trusted-keys", str(keys_file), "--now", "2030-05-31T23:59:59Z"], monkeypatch, tmp_path) == 0


def test_a_legacy_manifest_passes_only_while_the_switch_is_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = write(tmp_path, LEGACY)
    assert run([str(manifest), "--lang", "en"], monkeypatch, tmp_path) == 0
    assert "legacy manifest" in capsys.readouterr().out
    assert run([str(manifest), "--trusted-keys", str(keys_file), "--require-asymmetric-signature"], monkeypatch, tmp_path) == 1
    assert run([str(manifest), "--trusted-keys", str(keys_file)], monkeypatch, tmp_path, saved={"require_asymmetric_signature": True}) == 1
    assert run([str(manifest), "--trusted-keys", str(keys_file)], monkeypatch, tmp_path, damaged=True) == 1


def test_the_switch_can_come_from_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path) -> None:
    manifest = write(tmp_path, LEGACY)
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "none.json")
    monkeypatch.setenv("HYDRA_UMC_UPDATER_REQUIRE_ASYMMETRIC_SIGNATURE", "1")
    assert call([str(manifest), "--trusted-keys", str(keys_file)]) == 1
    monkeypatch.setenv("HYDRA_UMC_UPDATER_REQUIRE_ASYMMETRIC_SIGNATURE", "0")
    assert call([str(manifest), "--trusted-keys", str(keys_file)]) == 0


def test_a_signed_manifest_without_a_list_of_keys_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run([str(write(tmp_path, GOOD)), "--lang", "en"], monkeypatch, tmp_path) == 1
    assert "No file of trusted manifest keys" in capsys.readouterr().err


def test_a_damaged_list_of_keys_or_manifest_or_clock_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path) -> None:
    bad_keys = tmp_path / "bad.json"
    bad_keys.write_text("{}", encoding="utf-8")
    assert run([str(write(tmp_path, GOOD)), "--trusted-keys", str(bad_keys)], monkeypatch, tmp_path) == 1
    assert run([str(tmp_path / "missing.json"), "--trusted-keys", str(keys_file)], monkeypatch, tmp_path) == 1
    assert run([str(write(tmp_path, GOOD)), "--trusted-keys", str(keys_file), "--now", "yesterday"], monkeypatch, tmp_path) == 1


def test_the_json_output_names_the_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keys_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run([str(write(tmp_path, GOOD)), "--trusted-keys", str(keys_file), "--now", NOW, "--json"], monkeypatch, tmp_path) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown == {"ok": True, "code": "ok", "key_id": GOOD["key_id"], "require_asymmetric_signature": False}


def test_every_language_has_every_message_with_the_same_blanks() -> None:
    keys = sorted(k for k in i18n.TRANSLATIONS["en"] if k.startswith("mfsig_"))
    assert len(keys) == 14
    for lang, table in i18n.TRANSLATIONS.items():
        for key in keys:
            assert key in table, (lang, key)
            assert ("{key_id}" in table[key]) == ("{key_id}" in i18n.TRANSLATIONS["en"][key]), (lang, key)


def test_the_verdict_of_a_non_object_is_malformed() -> None:
    assert update_manifest.verify_manifest([], (), moment(NOW)).code == "malformed"  # type: ignore[arg-type]
