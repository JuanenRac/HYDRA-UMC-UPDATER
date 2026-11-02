# =============================================================================
# HYDRA-UMC-UPDATER - Verification of signed image releases: image_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Checks a signed release of an operating-system image before anything is done with the image.

The image builder publishes three things that must agree: the image, a `release.json` (format `hydra-image-release/1`)
that names the SHA-256 and size of the image, the version and the commit it was built from, and `release.json.sig`, an
Ed25519 signature over a domain tag plus the SHA-256 of the exact bytes of `release.json`. Optionally there is also a signed
git tag on that same commit. This module only READS: it reads the manifest, the signature, the image and the trusted keys,
runs `git verify-tag` when asked, and says yes or no. It writes nothing, installs nothing and never receives a private key.

Trust comes from a file of trusted PUBLIC keys that the person who runs the updater controls (one key per line, 64 hexadecimal
characters of a raw Ed25519 key, then an optional label; `revoke KEY` withdraws a key, `#` starts a comment). Several keys can be
trusted at once, which is how a key is rotated: add the new one, publish with it, revoke the old one. The fingerprint of the key
that signed a release is reported so it can be compared with the one published by the maintainer.

Fail closed: no trusted keys, an unusable keys file, no signature, a signature by a revoked or unknown key, the signature of
another domain (for example a signed profile), a different image (name, size or SHA-256), a manifest with wrong fields, a tag
without a valid signature or on another commit, or a machine without the `cryptography` package, all reject the release with a
reason (`ImageReleaseError.code`, translated by the command) and nothing else happens. The format, the domain and the order of
the checks are those of the release commands of the image builder (`release-manifest`, `release-sign`, `release-verify`).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FORMAT = "hydra-image-release/1"
DOMAIN = b"hydra-umc-os-rebuilder-release/1\n"
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_KEYS_FILE_BYTES = 256 * 1024
_HEX_KEY = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX_SIGNATURE = re.compile(r"^[0-9a-fA-F]{128}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_VERSION = re.compile(r"^[0-9]+(\.[0-9]+)*$")
_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


class ImageReleaseError(ValueError):
    """A release that is refused. `code` names the reason (a key of the translations: `imgrel_<code>`), `params` fill its blanks."""

    def __init__(self, code: str, english: str, **params: object) -> None:
        super().__init__(english)
        self.code = code
        self.params = params


@dataclass(frozen=True)
class TrustedKeys:
    active: tuple[str, ...]
    revoked: tuple[str, ...] = ()


@dataclass
class ImageReleaseResult:
    version: str
    tag: str
    commit: str
    fingerprint: str
    checked: list[str] = field(default_factory=list)


Runner = Callable[[list[str], Path], "subprocess.CompletedProcess[str]"]


def fingerprint(public_key_hex: str) -> str:
    """The first 16 hexadecimal characters of the SHA-256 of the raw public key, in groups of four."""
    digest = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:16]
    return ":".join(digest[i : i + 4] for i in range(0, 16, 4))


def load_trusted_keys(path: str | Path | None) -> TrustedKeys:
    """Read the file of trusted public keys. Missing, unreadable, malformed or without any active key: refused."""
    if not path or not str(path).strip():
        raise ImageReleaseError("no_keys_file", "no file of trusted keys is configured")
    keys_path = Path(str(path)).expanduser()
    try:
        if not keys_path.is_file():
            raise ImageReleaseError("keys_unreadable", f"the file of trusted keys {keys_path} does not exist", path=str(keys_path))
        if keys_path.stat().st_size > MAX_KEYS_FILE_BYTES:
            raise ImageReleaseError("keys_unreadable", f"the file of trusted keys {keys_path} is too large", path=str(keys_path))
        text = keys_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ImageReleaseError("keys_unreadable", f"the file of trusted keys {keys_path} cannot be read", path=str(keys_path)) from error
    active: list[str] = []
    revoked: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        target = active
        if parts[0].lower() == "revoke":
            target, parts = revoked, parts[1:]
        if not parts or not _HEX_KEY.match(parts[0]):
            raise ImageReleaseError("bad_key_line", f"line {number} of the trusted keys is not a 64-character hexadecimal key", line=number)
        target.append(parts[0].lower())
    usable = [key for key in dict.fromkeys(active) if key not in revoked]
    if not usable:
        raise ImageReleaseError("keys_empty", "the file of trusted keys holds no usable (unrevoked) key")
    return TrustedKeys(active=tuple(usable), revoked=tuple(dict.fromkeys(revoked)))


def _ed25519() -> tuple[Any, Any]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as error:
        raise ImageReleaseError("no_crypto", 'verifying a release needs the "cryptography" package: pip install "hydra-umc-updater[signing]"') from error
    return ed25519, InvalidSignature


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(manifest: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        with manifest.open("rb") as handle:
            content = handle.read(MAX_MANIFEST_BYTES + 1)
    except OSError as error:
        raise ImageReleaseError("manifest_unreadable", f"cannot read {manifest.name}", name=manifest.name) from error
    if len(content) > MAX_MANIFEST_BYTES:
        raise ImageReleaseError("manifest_unreadable", f"{manifest.name} is too large", name=manifest.name)
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ImageReleaseError("manifest_unreadable", f"{manifest.name} is not valid JSON", name=manifest.name) from error
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ImageReleaseError("bad_format", f"{manifest.name} is not a {FORMAT} file", name=manifest.name, expected=FORMAT)
    return content, data


def _check_fields(data: dict[str, Any]) -> None:
    def bad(name: str) -> ImageReleaseError:
        return ImageReleaseError("bad_field", f"the field {name!r} of the release is missing or malformed", field=name)

    image = data.get("image")
    if not isinstance(image, str) or not image or image != Path(image).name or image in {".", ".."}:
        raise bad("image")
    size = data.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise bad("size")
    if not isinstance(data.get("sha256"), str) or not _SHA256.match(data["sha256"]):
        raise bad("sha256")
    if not isinstance(data.get("version"), str) or not _VERSION.match(data["version"]):
        raise bad("version")
    if not isinstance(data.get("commit"), str) or not _COMMIT.match(data["commit"]):
        raise bad("commit")
    if not isinstance(data.get("tag"), str) or not _TAG.match(data["tag"]):
        raise bad("tag")


def verify_signature(manifest: Path, content: bytes, keys: TrustedKeys) -> str:
    """The manifest's `.sig` is a valid signature (this domain) of these exact bytes by an active trusted key; returns that key.
    A signature that only a revoked key makes is refused as such."""
    sig_file = manifest.with_name(manifest.name + ".sig")
    try:
        raw = sig_file.read_text(encoding="ascii").strip()
    except FileNotFoundError as error:
        raise ImageReleaseError("no_signature", f"{manifest.name} has no signature file ({sig_file.name})", name=sig_file.name) from error
    except (OSError, UnicodeDecodeError) as error:
        raise ImageReleaseError("no_signature", f"{sig_file.name} cannot be read", name=sig_file.name) from error
    if not _HEX_SIGNATURE.match(raw):
        raise ImageReleaseError("signature_malformed", f"{sig_file.name} is not a hexadecimal Ed25519 signature (128 characters)", name=sig_file.name)
    ed25519, invalid = _ed25519()
    message = DOMAIN + hashlib.sha256(content).hexdigest().encode("ascii")
    signature = bytes.fromhex(raw)

    def matches(key_hex: str) -> bool:
        try:
            ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex)).verify(signature, message)
        except (ValueError, invalid):
            return False
        return True

    for key in keys.active:
        if matches(key):
            return key
    if any(matches(key) for key in keys.revoked):
        raise ImageReleaseError("key_revoked", "the release is signed by a key that has been revoked")
    raise ImageReleaseError("signature_bad", "the signature does not verify against any trusted key: the manifest was changed, signed with another key or for another purpose")


def _run_git(command: list[str], cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60, check=False)


def verify_tag(repo: Path | None, tag: str, commit: str, run: Runner = _run_git) -> None:
    """The tag verifies (`git verify-tag`) and points at exactly the commit of the manifest."""
    if repo is None or not repo.is_dir():
        raise ImageReleaseError("tag_needs_repo", "a signed tag is required but no repository to check it in was given")
    try:
        checked = run(["git", "verify-tag", tag], repo)
        pointed = run(["git", "rev-list", "-n", "1", tag], repo) if checked.returncode == 0 else None
    except (OSError, subprocess.SubprocessError) as error:
        raise ImageReleaseError("git_unavailable", "git could not be run to check the tag") from error
    if checked.returncode != 0:
        raise ImageReleaseError("tag_unsigned", f"the tag {tag} has no valid signature", tag=tag)
    if pointed is None or pointed.returncode != 0 or pointed.stdout.strip() != commit:
        raise ImageReleaseError("tag_commit", f"the tag {tag} does not point at the commit of the release", tag=tag)


def verify_release(
    manifest: Path,
    image: Path,
    keys: TrustedKeys,
    *,
    require_tag: bool = False,
    repo: Path | None = None,
    run: Runner = _run_git,
) -> ImageReleaseResult:
    """Verify a release. Reads only. Order: the manifest is authenticated first, and only then are its fields trusted."""
    content, data = _read_manifest(manifest)
    key = verify_signature(manifest, content, keys)
    checked = ["signature"]
    _check_fields(data)
    try:
        if not image.is_file():
            raise OSError
        size = image.stat().st_size
        if image.name != data["image"]:
            raise ImageReleaseError("image_mismatch", "the image has another name than the release says", what="name")
        if size != data["size"]:
            raise ImageReleaseError("image_mismatch", "the image has another size than the release says", what="size")
        if file_sha256(image) != data["sha256"]:
            raise ImageReleaseError("image_mismatch", "the SHA-256 of the image is not the one in the release", what="sha256")
    except OSError as error:
        raise ImageReleaseError("image_unreadable", f"the image {image.name} cannot be read", name=image.name) from error
    checked.append("sha256")
    if require_tag:
        verify_tag(repo, data["tag"], data["commit"], run)
        checked.append("tag")
    return ImageReleaseResult(data["version"], data["tag"], data["commit"], fingerprint(key), checked)
