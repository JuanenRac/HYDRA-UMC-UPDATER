# =============================================================================
# HYDRA-UMC-UPDATER - Signed version trains: edges of the key files, the signature file and the switch (ephemeral test keys only)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import os
from pathlib import Path

import pytest

from hydra_umc_updater import settings, train, train_signing
from hydra_umc_updater.train_signing import TrainSigningError

ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
from cryptography.hazmat.primitives import serialization  # noqa: E402

HEX64 = "ab" * 32


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (train.TRAINS_ENV, train_signing.REQUIRE_SIGNED_ENV, train_signing.PUBKEY_ENV, train_signing.PRIVATE_KEY_FILE_ENV):
        monkeypatch.delenv(name, raising=False)


def pair(tmp: Path) -> tuple[Path, str]:
    private = ed25519.Ed25519PrivateKey.generate()
    seed = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    path = tmp / "k.key"
    path.write_text(seed.hex() + "\n", encoding="utf-8")
    if os.name == "posix":
        path.chmod(0o600)
    return path, public.hex()


def settings_say(monkeypatch: pytest.MonkeyPatch, values: dict, damaged: bool = False) -> None:
    monkeypatch.setattr(settings, "load_settings", lambda: dict(values))
    monkeypatch.setattr(settings, "settings_file_is_damaged", lambda: damaged)


class TestThePinnedPublicKey:
    def test_it_is_read_from_64_hexadecimal_characters(self):
        assert train_signing._public_key_bytes(HEX64) == bytes.fromhex(HEX64)
        assert train_signing._public_key_bytes("  " + HEX64.upper() + "  ") == bytes.fromhex(HEX64)

    def test_it_is_read_from_a_file_that_holds_them(self, tmp_path):
        path = tmp_path / "pub.txt"
        path.write_text(HEX64 + "\n", encoding="utf-8")
        assert train_signing._public_key_bytes(str(path)) == bytes.fromhex(HEX64)

    @pytest.mark.parametrize("source", ["xyz", "ab" * 31, "ab" * 33, "zz" * 32])
    def test_what_is_neither_hex_nor_a_file_is_refused(self, source):
        with pytest.raises(TrainSigningError, match="neither 64 hexadecimal characters nor an existing file"):
            train_signing._public_key_bytes(source)

    def test_a_missing_file_is_refused(self, tmp_path):
        with pytest.raises(TrainSigningError, match="neither 64 hexadecimal characters nor an existing file"):
            train_signing._public_key_bytes(str(tmp_path / "missing"))

    def test_a_file_with_the_wrong_content_is_refused(self, tmp_path):
        path = tmp_path / "pub.txt"
        path.write_text("not a key\n", encoding="utf-8")
        with pytest.raises(TrainSigningError, match="must be 64 hexadecimal"):
            train_signing._public_key_bytes(str(path))

    def test_a_file_that_is_not_text_is_refused(self, tmp_path):
        path = tmp_path / "pub.bin"
        path.write_bytes(b"\xff\xfe\x00\x80")
        with pytest.raises(TrainSigningError, match="cannot be read"):
            train_signing._public_key_bytes(str(path))


class TestThePrivateKeyFile:
    def test_a_missing_file_a_folder_and_a_wrong_content_are_each_refused(self, tmp_path):
        with pytest.raises(TrainSigningError, match="cannot be read"):
            train_signing._private_key_bytes(tmp_path / "missing.key")
        with pytest.raises(TrainSigningError, match="is not a file"):
            train_signing._private_key_bytes(tmp_path)
        wrong = tmp_path / "wrong.key"
        wrong.write_text("short\n", encoding="utf-8")
        if os.name == "posix":
            wrong.chmod(0o600)
        with pytest.raises(TrainSigningError, match="64 hexadecimal"):
            train_signing._private_key_bytes(wrong)
        binary = tmp_path / "binary.key"
        binary.write_bytes(b"\xff\xfe\x00\x80")
        if os.name == "posix":
            binary.chmod(0o600)
        with pytest.raises(TrainSigningError, match="cannot be read"):
            train_signing._private_key_bytes(binary)

    @pytest.mark.skipif(os.name != "posix", reason="owner-only permissions are checked on POSIX")
    def test_a_key_other_users_can_read_is_refused(self, tmp_path):
        path, _ = pair(tmp_path)
        path.chmod(0o644)
        with pytest.raises(TrainSigningError, match="owner only"):
            train_signing._private_key_bytes(path)


class TestSigning:
    def test_a_train_that_cannot_be_read_or_is_too_large_is_not_signed(self, tmp_path):
        key, _ = pair(tmp_path)
        with pytest.raises(TrainSigningError, match="cannot read the train"):
            train_signing.sign_train_file(tmp_path / "missing.json", key)
        big = tmp_path / "big.json"
        big.write_bytes(b"x" * (train_signing.MAX_TRAIN_BYTES + 1))
        with pytest.raises(TrainSigningError, match="too large"):
            train_signing.sign_train_file(big, key)

    def test_a_signature_is_exactly_for_the_bytes_it_was_made_over(self, tmp_path):
        key, public = pair(tmp_path)
        path = tmp_path / "t.json"
        path.write_bytes(b'{"a":1}\n')
        signature = train_signing.sign_train_file(path, key)
        assert train_signing.read_verified(path, public) == '{"a":1}\n'
        assert len(signature.read_text(encoding="ascii").strip()) == 128
        path.write_bytes(b'{"a":2}\n')
        with pytest.raises(TrainSigningError, match="does not match"):
            train_signing.read_verified(path, public)
        # a one-character change of the signature is just as wrong
        path.write_bytes(b'{"a":1}\n')
        text = signature.read_text(encoding="ascii").strip()
        signature.write_text(("0" if text[0] != "0" else "1") + text[1:] + "\n", encoding="ascii")
        with pytest.raises(TrainSigningError, match="does not match"):
            train_signing.read_verified(path, public)

    def test_a_signature_of_another_key_does_not_pass(self, tmp_path):
        key, _ = pair(tmp_path)
        (tmp_path / "other").mkdir()
        _, other_public = pair(tmp_path / "other")
        path = tmp_path / "t.json"
        path.write_bytes(b"{}\n")
        train_signing.sign_train_file(path, key)
        with pytest.raises(TrainSigningError, match="does not match"):
            train_signing.read_verified(path, other_public)


class TestVerifyingWhatArrives:
    def test_no_pinned_key_means_no_trust(self, tmp_path):
        with pytest.raises(TrainSigningError, match="no public key is pinned"):
            train_signing.verify_train_bytes(b"{}", tmp_path / "t.sig", None)
        with pytest.raises(TrainSigningError, match="no public key is pinned"):
            train_signing.verify_train_bytes(b"{}", tmp_path / "t.sig", "")

    def test_a_missing_or_unreadable_or_malformed_signature_file_is_refused(self, tmp_path):
        with pytest.raises(TrainSigningError, match="has no signature file"):
            train_signing.verify_train_bytes(b"{}", tmp_path / "t.sig", HEX64)
        binary = tmp_path / "bin.sig"
        binary.write_bytes(b"\xff\xfe\x00\x80")
        with pytest.raises(TrainSigningError, match="cannot be read"):
            train_signing.verify_train_bytes(b"{}", binary, HEX64)
        for text in ("", "abc", "zz" * 64, "ab" * 63, "ab" * 65):
            bad = tmp_path / "bad.sig"
            bad.write_text(text + "\n", encoding="ascii")
            with pytest.raises(TrainSigningError, match="not a hexadecimal Ed25519 signature"):
                train_signing.verify_train_bytes(b"{}", bad, HEX64)

    def test_a_pinned_key_that_is_not_a_key_is_refused(self, tmp_path):
        good_shape = tmp_path / "ok.sig"
        good_shape.write_text("ab" * 64 + "\n", encoding="ascii")
        with pytest.raises(TrainSigningError):
            train_signing.verify_train_bytes(b"{}", good_shape, "not hex")

    def test_a_train_that_is_not_utf8_is_refused_even_when_signed(self, tmp_path):
        key, public = pair(tmp_path)
        path = tmp_path / "t.json"
        path.write_bytes(b"\xff\xfe\x00\x80")
        train_signing.sign_train_file(path, key)
        with pytest.raises(TrainSigningError, match="not valid UTF-8"):
            train_signing.read_verified(path, public)

    def test_a_train_that_cannot_be_opened_or_is_too_large_is_refused(self, tmp_path):
        with pytest.raises(TrainSigningError, match="cannot read the train"):
            train_signing.read_verified(tmp_path / "missing.json", HEX64)
        big = tmp_path / "big.json"
        big.write_bytes(b"x" * (train_signing.MAX_TRAIN_BYTES + 1))
        with pytest.raises(TrainSigningError, match="too large"):
            train_signing.read_verified(big, HEX64)


class TestTheSwitchAndThePin:
    @pytest.mark.parametrize("value", ["1", "true", "YES", " on "])
    def test_the_environment_can_require_signatures(self, monkeypatch, value):
        monkeypatch.setenv(train_signing.REQUIRE_SIGNED_ENV, value)
        assert train_signing.require_signed_trains() is True
        assert train_signing.signatures_explicitly_off() is False

    @pytest.mark.parametrize("value", ["0", "false", "No", " off "])
    def test_the_environment_can_turn_them_off_in_so_many_words(self, monkeypatch, value):
        monkeypatch.setenv(train_signing.REQUIRE_SIGNED_ENV, value)
        assert train_signing.require_signed_trains() is False
        assert train_signing.signatures_explicitly_off() is True

    def test_a_damaged_settings_file_never_turns_the_requirement_off(self, monkeypatch):
        settings_say(monkeypatch, {train_signing.SETTING_REQUIRE: False}, damaged=True)
        assert train_signing.require_signed_trains() is True
        assert train_signing.signatures_explicitly_off() is False

    def test_the_saved_setting_counts_when_the_environment_says_nothing(self, monkeypatch):
        settings_say(monkeypatch, {train_signing.SETTING_REQUIRE: False})
        assert train_signing.require_signed_trains() is False
        assert train_signing.signatures_explicitly_off() is True
        settings_say(monkeypatch, {train_signing.SETTING_REQUIRE: True})
        assert train_signing.require_signed_trains() is True
        assert train_signing.signatures_explicitly_off() is False

    def test_a_saved_value_that_is_not_a_boolean_falls_back_to_the_default(self, monkeypatch):
        settings_say(monkeypatch, {train_signing.SETTING_REQUIRE: "no"})
        assert train_signing.require_signed_trains() is train.trains_enabled()
        assert train_signing.signatures_explicitly_off() is False

    def test_the_pinned_key_comes_from_the_environment_first_then_the_settings(self, monkeypatch):
        settings_say(monkeypatch, {train_signing.SETTING_PUBKEY: "  " + HEX64 + "  "})
        assert train_signing.configured_public_key() == HEX64
        monkeypatch.setenv(train_signing.PUBKEY_ENV, "cd" * 32)
        assert train_signing.configured_public_key() == "cd" * 32
        monkeypatch.delenv(train_signing.PUBKEY_ENV)
        settings_say(monkeypatch, {train_signing.SETTING_PUBKEY: "   "})
        assert train_signing.configured_public_key() is None
        settings_say(monkeypatch, {train_signing.SETTING_PUBKEY: 7})
        assert train_signing.configured_public_key() is None


class TestMakingAKeyPair:
    @pytest.mark.parametrize("name", ["", ".hidden", "a/b", "a b", "x" * 65])
    def test_a_name_that_could_leave_the_folder_is_refused(self, tmp_path, name):
        with pytest.raises(TrainSigningError, match="may only hold letters"):
            train_signing.generate_train_keypair(tmp_path, name)

    def test_a_pair_is_written_once_and_never_overwritten(self, tmp_path):
        private_path, public_path = train_signing.generate_train_keypair(tmp_path / "keys", "t1")
        assert private_path.name == "t1.key" and public_path.name == "t1.pub"
        assert len(private_path.read_text(encoding="utf-8").strip()) == 64
        assert len(public_path.read_text(encoding="utf-8").strip()) == 64
        if os.name == "posix":
            assert (private_path.stat().st_mode & 0o077) == 0
        before = private_path.read_text(encoding="utf-8")
        with pytest.raises(TrainSigningError, match="nothing was overwritten"):
            train_signing.generate_train_keypair(tmp_path / "keys", "t1")
        assert private_path.read_text(encoding="utf-8") == before
        # and the pair works: a train signed with it verifies with its public half
        path = tmp_path / "train.json"
        path.write_bytes(b"{}\n")
        train_signing.sign_train_file(path, private_path)
        assert train_signing.read_verified(path, public_path.read_text(encoding="utf-8").strip()) == "{}\n"

    def test_a_folder_that_cannot_be_made_leaves_no_half_pair(self, tmp_path):
        blocker = tmp_path / "blocker"
        blocker.write_text("a file where a folder should be", encoding="utf-8")
        with pytest.raises(TrainSigningError, match="cannot be written"):
            train_signing.generate_train_keypair(blocker / "keys", "t2")
        assert not (blocker / "keys").exists()
