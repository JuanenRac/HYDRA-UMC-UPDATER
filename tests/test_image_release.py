# =============================================================================
# HYDRA-UMC-UPDATER - Verification of signed image releases (ephemeral test keys only)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The releases are built here the way the image builder builds them (format, domain tag, SHA-256 of the manifest bytes), with
keys made in memory for each test, so nothing real is signed, read or written outside the temporary folder."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from hydra_umc_updater import i18n, image_release, main

ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
from cryptography.hazmat.primitives import serialization  # noqa: E402

COMMIT = "a" * 40
IMAGE_BYTES = b"not a real image"
OLD_DOMAIN = b"hydra-umc-os-rebuilder-release/1\n"


def new_key() -> tuple[object, str]:
    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return private, public


def make_release(tmp: Path, private, *, domain: bytes = OLD_DOMAIN, **overrides) -> tuple[Path, Path]:
    image = tmp / "hydra.img"
    image.write_bytes(IMAGE_BYTES)
    data = {
        "format": "hydra-image-release/1", "image": image.name, "size": len(IMAGE_BYTES),
        "sha256": hashlib.sha256(IMAGE_BYTES).hexdigest(), "version": "0.4.0", "commit": COMMIT, "tag": "image-v0.4.0",
    }
    data.update(overrides)
    manifest = tmp / "release.json"
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sign(manifest, private, domain)
    return manifest, image


def sign(manifest: Path, private, domain: bytes = OLD_DOMAIN) -> None:
    message = domain + hashlib.sha256(manifest.read_bytes()).hexdigest().encode("ascii")
    manifest.with_name(manifest.name + ".sig").write_text(private.sign(message).hex() + "\n", encoding="utf-8")


def keys_file(tmp: Path, *lines: str) -> Path:
    path = tmp / "trusted_keys.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class Git:
    def __init__(self, valid: bool, commit: str) -> None:
        self.valid, self.commit, self.calls = valid, commit, []

    def __call__(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        if command[:2] == ["git", "verify-tag"]:
            return subprocess.CompletedProcess(command, 0 if self.valid else 1, "", "" if self.valid else "no signature")
        return subprocess.CompletedProcess(command, 0, self.commit + "\n", "")


def code_of(excinfo) -> str:
    return excinfo.value.code


def test_a_good_release_verifies_and_reports_the_key_fingerprint(tmp_path: Path) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = image_release.load_trusted_keys(keys_file(tmp_path, f"{public} release key of the maintainer  # comment"))
    result = image_release.verify_release(manifest, image, keys)
    assert result.checked == ["signature", "sha256"] and result.version == "0.4.0" and result.tag == "image-v0.4.0"
    assert result.fingerprint == image_release.fingerprint(public) and len(result.fingerprint) == 19


def test_the_tag_is_checked_on_the_same_commit_when_asked(tmp_path: Path) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = image_release.load_trusted_keys(keys_file(tmp_path, public))
    ok = image_release.verify_release(manifest, image, keys, require_tag=True, repo=tmp_path, run=Git(True, COMMIT))
    assert ok.checked == ["signature", "sha256", "tag"]
    with pytest.raises(image_release.ImageReleaseError) as bad_tag:
        image_release.verify_release(manifest, image, keys, require_tag=True, repo=tmp_path, run=Git(False, COMMIT))
    assert code_of(bad_tag) == "tag_unsigned"
    with pytest.raises(image_release.ImageReleaseError) as other_commit:
        image_release.verify_release(manifest, image, keys, require_tag=True, repo=tmp_path, run=Git(True, "b" * 40))
    assert code_of(other_commit) == "tag_commit"
    with pytest.raises(image_release.ImageReleaseError) as no_repo:
        image_release.verify_release(manifest, image, keys, require_tag=True, run=Git(True, COMMIT))
    assert code_of(no_repo) == "tag_needs_repo"
    # without the option the tag is not looked at
    git = Git(False, COMMIT)
    image_release.verify_release(manifest, image, keys, run=git)
    assert git.calls == []


@pytest.mark.parametrize("hostile", ["-x", "--output=/tmp/x", "a b", "../x", ""])
def test_a_hostile_tag_name_never_reaches_git(tmp_path: Path, hostile: str) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private, tag=hostile)
    keys = image_release.load_trusted_keys(keys_file(tmp_path, public))
    git = Git(True, COMMIT)
    with pytest.raises(image_release.ImageReleaseError) as error:
        image_release.verify_release(manifest, image, keys, require_tag=True, repo=tmp_path, run=git)
    assert code_of(error) == "bad_field" and git.calls == []


def test_no_signature_or_a_malformed_one_is_refused(tmp_path: Path) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = image_release.load_trusted_keys(keys_file(tmp_path, public))
    sig = manifest.with_name("release.json.sig")
    sig.write_text("zz\n", encoding="utf-8")
    with pytest.raises(image_release.ImageReleaseError) as malformed:
        image_release.verify_release(manifest, image, keys)
    assert code_of(malformed) == "signature_malformed"
    sig.unlink()
    with pytest.raises(image_release.ImageReleaseError) as missing:
        image_release.verify_release(manifest, image, keys)
    assert code_of(missing) == "no_signature"


def test_another_domain_another_key_or_a_changed_manifest_is_refused(tmp_path: Path) -> None:
    private, public = new_key()
    _, stranger = new_key()
    manifest, image = make_release(tmp_path, private, domain=b"hydra-umc-os-rebuilder-profile/1\n")  # a profile signature
    with pytest.raises(image_release.ImageReleaseError) as domain:
        image_release.verify_release(manifest, image, image_release.load_trusted_keys(keys_file(tmp_path, public)))
    assert code_of(domain) == "signature_bad"
    sign(manifest, private)
    with pytest.raises(image_release.ImageReleaseError) as other_key:
        image_release.verify_release(manifest, image, image_release.load_trusted_keys(keys_file(tmp_path, stranger)))
    assert code_of(other_key) == "signature_bad"
    keys = image_release.load_trusted_keys(keys_file(tmp_path, public))
    image_release.verify_release(manifest, image, keys)
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("0.4.0", "0.4.1"), encoding="utf-8")
    with pytest.raises(image_release.ImageReleaseError) as changed:
        image_release.verify_release(manifest, image, keys)
    assert code_of(changed) == "signature_bad"


def test_a_different_image_is_refused_by_hash_size_and_name(tmp_path: Path) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = image_release.load_trusted_keys(keys_file(tmp_path, public))
    image.write_bytes(b"x" * len(IMAGE_BYTES))  # same size, other content
    with pytest.raises(image_release.ImageReleaseError) as same_size:
        image_release.verify_release(manifest, image, keys)
    assert same_size.value.params == {"what": "sha256"}
    image.write_bytes(IMAGE_BYTES + b"!")
    with pytest.raises(image_release.ImageReleaseError) as size:
        image_release.verify_release(manifest, image, keys)
    assert size.value.params == {"what": "size"}
    image.write_bytes(IMAGE_BYTES)
    renamed = tmp_path / "other.img"
    renamed.write_bytes(IMAGE_BYTES)
    with pytest.raises(image_release.ImageReleaseError) as name:
        image_release.verify_release(manifest, renamed, keys)
    assert name.value.params == {"what": "name"}
    with pytest.raises(image_release.ImageReleaseError) as gone:
        image_release.verify_release(manifest, tmp_path / "hydra.img.missing", keys)
    assert code_of(gone) in {"image_unreadable", "image_mismatch"}


@pytest.mark.parametrize(
    "override",
    [{"format": "hydra-image-release/2"}, {"sha256": "ABC"}, {"size": "7"}, {"size": True}, {"commit": "abc"}, {"version": "v1"}, {"image": "../hydra.img"}],
)
def test_a_malformed_manifest_is_refused_even_when_signed(tmp_path: Path, override: dict) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private, **override)
    with pytest.raises(image_release.ImageReleaseError) as error:
        image_release.verify_release(manifest, image, image_release.load_trusted_keys(keys_file(tmp_path, public)))
    assert code_of(error) in {"bad_format", "bad_field"}


def test_not_json_or_too_big_is_refused(tmp_path: Path) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = image_release.load_trusted_keys(keys_file(tmp_path, public))
    manifest.write_bytes(b"\xff\xfe")
    with pytest.raises(image_release.ImageReleaseError) as binary:
        image_release.verify_release(manifest, image, keys)
    assert code_of(binary) == "manifest_unreadable"
    manifest.write_bytes(b" " * (image_release.MAX_MANIFEST_BYTES + 1))
    with pytest.raises(image_release.ImageReleaseError) as big:
        image_release.verify_release(manifest, image, keys)
    assert code_of(big) == "manifest_unreadable"


def test_the_trusted_keys_file_fails_closed(tmp_path: Path) -> None:
    for source, wanted in [(None, "no_keys_file"), ("", "no_keys_file"), (tmp_path / "missing.txt", "keys_unreadable")]:
        with pytest.raises(image_release.ImageReleaseError) as error:
            image_release.load_trusted_keys(source)
        assert code_of(error) == wanted
    with pytest.raises(image_release.ImageReleaseError) as empty:
        image_release.load_trusted_keys(keys_file(tmp_path, "# only a comment", ""))
    assert code_of(empty) == "keys_empty"
    with pytest.raises(image_release.ImageReleaseError) as bad:
        image_release.load_trusted_keys(keys_file(tmp_path, "# header", "1234"))
    assert code_of(bad) == "bad_key_line" and bad.value.params == {"line": 2}
    _, only = new_key()
    with pytest.raises(image_release.ImageReleaseError) as revoked_only:
        image_release.load_trusted_keys(keys_file(tmp_path, only, f"revoke {only}"))
    assert code_of(revoked_only) == "keys_empty"


def test_rotation_trusts_both_keys_until_the_old_one_is_revoked(tmp_path: Path) -> None:
    old_private, old_public = new_key()
    new_private, new_public = new_key()
    old_manifest, image = make_release(tmp_path, old_private)
    both = image_release.load_trusted_keys(keys_file(tmp_path, old_public, new_public))
    assert image_release.verify_release(old_manifest, image, both).fingerprint == image_release.fingerprint(old_public)
    sign(old_manifest, new_private)
    assert image_release.verify_release(old_manifest, image, both).fingerprint == image_release.fingerprint(new_public)
    sign(old_manifest, old_private)
    rotated = image_release.load_trusted_keys(keys_file(tmp_path, old_public, new_public, f"revoke {old_public}"))
    with pytest.raises(image_release.ImageReleaseError) as error:
        image_release.verify_release(old_manifest, image, rotated)
    assert code_of(error) == "key_revoked"


# --- the command ---------------------------------------------------------------------------------------------------------


def run_cli(*argv: str) -> int:
    args = main.build_parser().parse_args(["image", "verify", *argv])
    return args.func(args)


def test_the_command_exits_zero_only_when_the_release_holds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = keys_file(tmp_path, public)
    assert run_cli(str(manifest), str(image), "--trusted-keys", str(keys), "--lang", "en", "--json") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["checked"] == ["signature", "sha256"] and out["key_fingerprint"] == image_release.fingerprint(public)
    before = sorted(p.name for p in tmp_path.iterdir())
    image.write_bytes(b"tampered image....")
    assert run_cli(str(manifest), str(image), "--trusted-keys", str(keys), "--lang", "en") == 1
    err = capsys.readouterr().err
    assert "does not match" in err and "nothing was applied" in err
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # nothing was written


def test_the_command_without_trusted_keys_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for name in ("HYDRA_UMC_UPDATER_IMAGE_TRUSTED_KEYS", "HYDRA_UMC_UPDATER_IMAGE_REQUIRE_TAG", "HYDRA_UMC_UPDATER_IMAGE_RELEASE_REPO"):
        monkeypatch.delenv(name, raising=False)
    private, _ = new_key()
    manifest, image = make_release(tmp_path, private)
    assert run_cli(str(manifest), str(image), "--lang", "es") == 1
    assert "claves de confianza" in capsys.readouterr().err


def test_the_command_reads_the_configuration_and_the_tag_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    private, public = new_key()
    manifest, image = make_release(tmp_path, private)
    keys = keys_file(tmp_path, public)
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_TRUSTED_KEYS", str(keys))
    assert run_cli(str(manifest), str(image), "--lang", "en") == 0
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_REQUIRE_TAG", "1")  # now a tag is required and there is no repository
    assert run_cli(str(manifest), str(image), "--lang", "en") == 1
    monkeypatch.delenv("HYDRA_UMC_UPDATER_IMAGE_REQUIRE_TAG")
    main.settings.save_settings(image_release_require_tag=True, image_release_trusted_keys=str(keys))
    monkeypatch.delenv("HYDRA_UMC_UPDATER_IMAGE_TRUSTED_KEYS")
    assert run_cli(str(manifest), str(image), "--lang", "en") == 1
    assert main.settings.get_image_release_require_tag() is True


def test_a_damaged_settings_file_keeps_the_tag_switch_off_but_signature_stays_required(tmp_path: Path) -> None:
    main.settings.SETTINGS_PATH.write_text("{not json", encoding="utf-8")
    assert main.settings.get_image_release_require_tag() is False
    private, _ = new_key()
    manifest, image = make_release(tmp_path, private)
    assert run_cli(str(manifest), str(image), "--lang", "en") == 1


def test_every_message_of_the_command_exists_in_the_eight_languages() -> None:
    codes = {
        "no_keys_file", "keys_unreadable", "keys_empty", "bad_key_line", "manifest_unreadable", "bad_format", "bad_field", "no_signature",
        "signature_malformed", "key_revoked", "signature_bad", "no_crypto", "image_unreadable", "image_mismatch", "tag_needs_repo",
        "tag_unsigned", "tag_commit", "git_unavailable", "rejected", "ok",
    }
    assert len(i18n.TRANSLATIONS) == 8
    for lang, table in i18n.TRANSLATIONS.items():
        assert {key[len("imgrel_"):] for key in table if key.startswith("imgrel_")} == codes, lang
