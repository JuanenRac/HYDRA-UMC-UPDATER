# =============================================================================
# HYDRA-UMC-UPDATER - Signed version trains (ephemeral test keys only)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from hydra_umc_updater import main, settings, train, train_signing

ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
from cryptography.hazmat.primitives import serialization  # noqa: E402

AAA = "HYDRA-UMC-AAA"
GOOD = {
    "schema_version": "1.0",
    "ecosystem": "HYDRA-UMC",
    "repositories": [{"name": AAA, "version": "1.0.0", "commit": "a" * 40}],
}


def new_pair(tmp: Path, label: str = "k") -> tuple[Path, str]:
    """An ephemeral key pair: the private seed goes to an owner-only file in the test folder, the public key is returned as hex."""
    private = ed25519.Ed25519PrivateKey.generate()
    seed = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    path = tmp / f"{label}.key"
    path.write_text(seed.hex() + "\n", encoding="utf-8")
    if os.name == "posix":
        path.chmod(0o600)
    return path, public.hex()


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (train.TRAINS_ENV, train_signing.REQUIRE_SIGNED_ENV, train_signing.PUBKEY_ENV, train_signing.PRIVATE_KEY_FILE_ENV):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def train_file(tmp_path: Path) -> Path:
    path = tmp_path / "ecosystem-release.json"
    path.write_text(json.dumps(GOOD, indent=2) + "\n", encoding="utf-8")
    return path


def sig_of(path: Path) -> Path:
    return path.with_name(path.name + ".sig")


def cli(capsys, *argv: str) -> tuple[int, str, str]:
    args = main.build_parser().parse_args(["train", *argv])
    code = args.func(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ----------------------------------------------------------------------------- the switch ------------------------

def test_signatures_follow_the_train_switch_by_default(monkeypatch):
    assert train_signing.require_signed_trains() is False  # trains off: nothing changes for anyone
    monkeypatch.setenv(train.TRAINS_ENV, "1")
    assert train_signing.require_signed_trains() is True  # trains on: signed unless someone says otherwise
    settings.save_settings(require_signed_trains=False)
    assert train_signing.require_signed_trains() is False
    settings.save_settings(require_signed_trains=True)
    monkeypatch.delenv(train.TRAINS_ENV)
    assert train_signing.require_signed_trains() is True
    monkeypatch.setenv(train_signing.REQUIRE_SIGNED_ENV, "0")
    assert train_signing.require_signed_trains() is False
    monkeypatch.setenv(train_signing.REQUIRE_SIGNED_ENV, "yes")
    assert train_signing.require_signed_trains() is True


def test_a_damaged_settings_file_means_required():
    settings.SETTINGS_PATH.write_text("[broken", encoding="utf-8")
    assert train_signing.require_signed_trains() is True


# ----------------------------------------------------------------------------- sign and verify ------------------

def test_a_signed_train_loads_with_the_pinned_key(tmp_path, train_file):
    key_file, public = new_pair(tmp_path)
    target = train_signing.sign_train_file(train_file, key_file)
    assert target == sig_of(train_file)
    assert len(target.read_text().strip()) == 128
    loaded = train.load_signed_train(train_file, public)
    assert [repo.name for repo in loaded.repos] == [AAA]


def test_the_pinned_key_may_be_a_file(tmp_path, train_file):
    key_file, public = new_pair(tmp_path)
    train_signing.sign_train_file(train_file, key_file)
    pub_file = tmp_path / "train.pub"
    pub_file.write_text(public + "\n", encoding="utf-8")
    assert train.load_signed_train(train_file, str(pub_file)).repos


def test_every_failure_is_refused(tmp_path, train_file):
    key_file, public = new_pair(tmp_path)
    _, other_public = new_pair(tmp_path, "other")
    with pytest.raises(train.TrainError, match="no signature file"):
        train.load_signed_train(train_file, public)
    train_signing.sign_train_file(train_file, key_file)
    with pytest.raises(train.TrainError, match="no public key is pinned"):
        train.load_signed_train(train_file, None)
    with pytest.raises(train.TrainError, match="does not match"):
        train.load_signed_train(train_file, other_public)  # signed by someone else
    good_signature = sig_of(train_file).read_text()
    train_file.write_text(train_file.read_text().replace("1.0.0", "1.0.1"), encoding="utf-8")
    with pytest.raises(train.TrainError, match="does not match"):
        train.load_signed_train(train_file, public)  # changed after signing
    for garbage in ("", "zz", "ab" * 10, "g" * 128):
        sig_of(train_file).write_text(garbage, encoding="utf-8")
        with pytest.raises(train.TrainError, match="hexadecimal"):
            train.load_signed_train(train_file, public)
    sig_of(train_file).write_text(good_signature, encoding="utf-8")
    for bad_key in ("not-a-key", "ab" * 31, str(tmp_path / "missing.pub")):
        with pytest.raises(train.TrainError):
            train.load_signed_train(train_file, bad_key)


def test_a_signature_does_not_transfer_to_other_content(tmp_path, train_file):
    key_file, public = new_pair(tmp_path)
    train_signing.sign_train_file(train_file, key_file)
    other = tmp_path / "other.json"
    other.write_text(train_file.read_text().replace("1.0.0", "2.0.0"), encoding="utf-8")
    sig_of(other).write_text(sig_of(train_file).read_text(), encoding="utf-8")
    with pytest.raises(train.TrainError, match="does not match"):
        train.load_signed_train(other, public)


def test_no_cryptography_package_fails_closed(tmp_path, train_file, monkeypatch):
    key_file, public = new_pair(tmp_path)
    train_signing.sign_train_file(train_file, key_file)
    monkeypatch.setitem(sys.modules, "cryptography.exceptions", None)
    with pytest.raises(train.TrainError, match="cryptography"):
        train.load_signed_train(train_file, public)


@pytest.mark.skipif(os.name != "posix", reason="file modes")
def test_a_private_key_readable_by_others_is_refused(tmp_path, train_file):
    key_file, _ = new_pair(tmp_path)
    key_file.chmod(0o644)
    with pytest.raises(train_signing.TrainSigningError, match="owner only"):
        train_signing.sign_train_file(train_file, key_file)


def test_a_malformed_private_key_is_refused_without_echoing_it(tmp_path, train_file):
    key_file = tmp_path / "bad.key"
    key_file.write_text("SECRET-NOT-HEX\n", encoding="utf-8")
    if os.name == "posix":
        key_file.chmod(0o600)
    with pytest.raises(train_signing.TrainSigningError) as caught:
        train_signing.sign_train_file(train_file, key_file)
    assert "SECRET-NOT-HEX" not in str(caught.value)


# ----------------------------------------------------------------------------- command line ---------------------

def test_sign_command_writes_the_signature_and_never_prints_the_key(tmp_path, train_file, capsys):
    key_file, public = new_pair(tmp_path)
    seed = key_file.read_text().strip()
    code, out, err = cli(capsys, "sign", str(train_file), "--key-file", str(key_file))
    assert code == 0
    assert seed not in out + err and public not in out + err
    assert train.load_signed_train(train_file, public).repos


def test_sign_command_needs_a_key_and_a_valid_train(tmp_path, train_file, capsys, monkeypatch):
    code, _, err = cli(capsys, "sign", str(train_file))
    assert code == 1 and "--key-file" in err
    key_file, _ = new_pair(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": "1.0"}', encoding="utf-8")
    code, _, err = cli(capsys, "sign", str(bad), "--key-file", str(key_file))
    assert code == 1 and "ERROR" in err and not sig_of(bad).exists()
    monkeypatch.setenv(train_signing.PRIVATE_KEY_FILE_ENV, str(key_file))
    code, _, _ = cli(capsys, "sign", str(train_file))
    assert code == 0


def test_plan_refuses_an_unsigned_train_when_required_and_accepts_it_when_signed(tmp_path, train_file, capsys, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    key_file, public = new_pair(tmp_path)
    plan = ("plan", str(train_file), "--offline", "--workspace", str(workspace))
    monkeypatch.setenv(train.TRAINS_ENV, "1")

    code, _, err = cli(capsys, *plan)
    assert code == 1 and "signature check failed" in err and "no public key is pinned" in err

    settings.save_settings(train_public_key=public)
    code, _, err = cli(capsys, *plan)
    assert code == 1 and "no signature file" in err  # a pinned key alone proves nothing without a signature

    train_signing.sign_train_file(train_file, key_file)
    code, out, _ = cli(capsys, *plan)
    assert code == 0 and "INSTALL" in out

    train_file.write_text(train_file.read_text().replace("1.0.0", "1.0.1"), encoding="utf-8")
    code, _, err = cli(capsys, *plan)
    assert code == 1 and "does not match" in err

    monkeypatch.setenv(train_signing.REQUIRE_SIGNED_ENV, "0")  # the explicit opt-out restores the old behaviour
    code, out, _ = cli(capsys, *plan)
    assert code == 0 and "INSTALL" in out


def test_apply_with_yes_installs_nothing_for_an_unsigned_train(tmp_path, train_file, capsys, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv(train.TRAINS_ENV, "1")
    code, _, err = cli(capsys, "apply", str(train_file), "--offline", "--yes", "--workspace", str(workspace))
    assert code == 1 and "signature check failed" in err
    assert not (workspace / AAA).exists() and not (workspace / train.STATE_DIR).exists()
