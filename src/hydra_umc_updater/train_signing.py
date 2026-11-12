# =============================================================================
# HYDRA-UMC-UPDATER - Signed version trains: train_signing.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Ed25519 signature of a version-train file.

A train decides which commit of which repository gets installed, so whoever can change the file changes what runs.
`train sign` writes `<train>.sig` next to the file: an Ed25519 signature over a domain tag plus the SHA-256 of the
file's exact bytes. Verification uses a public key pinned in the configuration (`train_public_key` in the saved
settings or `HYDRA_UMC_UPDATER_TRAIN_PUBKEY`; 64 hexadecimal characters, or a file holding them).

The signature is required when the switch `require_signed_trains` says so. Unset, it follows the version-train switch:
whenever trains are on, a signature is required (fail closed). Explicitly `false` (or `HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS=0`)
turns it off. A damaged settings file means "required". With the signature required, a train with no signature,
a wrong signature, no pinned key, an unusable key or no `cryptography` package is refused; nothing is ever assumed.

Keys are raw 32-byte Ed25519 keys written as 64 hexadecimal characters. A private key is only ever read from a file
(never from a command line, never printed, never written by this tool), and on POSIX that file must not be readable
by anyone but its owner. Every message names the file or the setting, never a key. Needs the optional `cryptography`
package (`pip install "hydra-umc-updater[signing]"`); the rest of the updater stays standard-library only.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any

from . import settings

REQUIRE_SIGNED_ENV = "HYDRA_UMC_UPDATER_REQUIRE_SIGNED_TRAINS"
PUBKEY_ENV = "HYDRA_UMC_UPDATER_TRAIN_PUBKEY"
PRIVATE_KEY_FILE_ENV = "HYDRA_UMC_UPDATER_TRAIN_KEY_FILE"
SETTING_REQUIRE = "require_signed_trains"
SETTING_PUBKEY = "train_public_key"
_DOMAIN = b"hydra-umc-updater-train/1\n"
_HEX_KEY = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX_SIGNATURE = re.compile(r"^[0-9a-fA-F]{128}$")
MAX_TRAIN_BYTES = 4 * 1024 * 1024
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


class TrainSigningError(ValueError):
    """A key, a signature or a train file that cannot be used. Messages never contain key material."""


def signature_path(train_path: Path) -> Path:
    return train_path.with_name(train_path.name + ".sig")


def _message(content: bytes) -> bytes:
    return _DOMAIN + hashlib.sha256(content).hexdigest().encode("ascii")


def _ed25519() -> tuple[Any, Any]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as error:
        raise TrainSigningError(
            'signed trains need the "cryptography" package: pip install "hydra-umc-updater[signing]"'
        ) from error
    return ed25519, InvalidSignature


def require_signed_trains() -> bool:
    """The switch. Environment first, then the saved settings, then the default (required whenever trains are on)."""
    from . import train  # local import: train imports this module's helpers lazily too

    value = os.environ.get(REQUIRE_SIGNED_ENV, "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    if settings.settings_file_is_damaged():
        return True
    saved = settings.load_settings().get(SETTING_REQUIRE)
    if isinstance(saved, bool):
        return saved
    return train.trains_enabled()


def signatures_explicitly_off() -> bool:
    """True only when the environment or the saved settings say, in so many words, that a train need not be signed."""
    value = os.environ.get(REQUIRE_SIGNED_ENV, "").strip().lower()
    if value in _FALSE:
        return True
    if value in _TRUE or settings.settings_file_is_damaged():
        return False
    return settings.load_settings().get(SETTING_REQUIRE) is False


def configured_public_key() -> str | None:
    """What the configuration pins as the trusted key (hex or a file path), or None. Never validated here."""
    env = os.environ.get(PUBKEY_ENV, "").strip()
    if env:
        return env
    saved = settings.load_settings().get(SETTING_PUBKEY)
    return saved.strip() if isinstance(saved, str) and saved.strip() else None


def _public_key_bytes(source: str) -> bytes:
    """A public key given as 64 hex characters or as the path of a file holding them."""
    text = source.strip()
    if not _HEX_KEY.match(text):
        path = Path(source)
        try:
            is_file = path.is_file()
        except OSError:
            is_file = False
        if not is_file:
            raise TrainSigningError("the pinned public key is neither 64 hexadecimal characters nor an existing file")
        try:
            text = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as error:
            raise TrainSigningError("the file with the pinned public key cannot be read") from error
    if not _HEX_KEY.match(text):
        raise TrainSigningError("the pinned public key must be 64 hexadecimal characters (a raw 32-byte Ed25519 key)")
    return bytes.fromhex(text)


def _private_key_bytes(path: Path) -> bytes:
    try:
        info = path.stat()
    except OSError as error:
        raise TrainSigningError(f"the private key file {path} cannot be read") from error
    if not stat.S_ISREG(info.st_mode):
        raise TrainSigningError(f"the private key {path} is not a file")
    if os.name == "posix" and info.st_mode & 0o077:
        raise TrainSigningError(f"the private key file {path} must be readable by its owner only (chmod 600)")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise TrainSigningError(f"the private key file {path} cannot be read") from error
    if not _HEX_KEY.match(text):
        raise TrainSigningError(f"the private key file {path} must hold 64 hexadecimal characters (a raw 32-byte Ed25519 key)")
    return bytes.fromhex(text)


def sign_train_file(train_path: Path, private_key_file: Path) -> Path:
    """Write `<train>.sig` for the train as it is now. Returns the signature path. Nothing about the key is kept."""
    ed25519, _ = _ed25519()
    try:
        content = train_path.read_bytes()
    except OSError as error:
        raise TrainSigningError(f"cannot read the train {train_path}: {error.strerror or error}") from error
    if len(content) > MAX_TRAIN_BYTES:
        raise TrainSigningError("the train file is too large")
    key = ed25519.Ed25519PrivateKey.from_private_bytes(_private_key_bytes(private_key_file))
    target = signature_path(train_path)
    target.write_text(key.sign(_message(content)).hex() + "\n", encoding="utf-8", newline="\n")
    return target


def verify_train_bytes(content: bytes, signature_file: Path, public_key: str | None) -> None:
    """Raise TrainSigningError unless `signature_file` holds a valid signature of exactly these bytes by the pinned key."""
    if not public_key:
        raise TrainSigningError(
            f"signed trains are required but no public key is pinned (set `{SETTING_PUBKEY}` in the settings or {PUBKEY_ENV})"
        )
    ed25519, invalid_signature = _ed25519()
    try:
        raw_signature = signature_file.read_text(encoding="ascii").strip()
    except FileNotFoundError as error:
        raise TrainSigningError(f"the train has no signature file ({signature_file.name}) and signed trains are required") from error
    except (OSError, UnicodeDecodeError) as error:
        raise TrainSigningError(f"the signature file {signature_file.name} cannot be read") from error
    if not _HEX_SIGNATURE.match(raw_signature):
        raise TrainSigningError(f"{signature_file.name} is not a hexadecimal Ed25519 signature (128 characters)")
    key_bytes = _public_key_bytes(public_key)
    try:
        key = ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)
    except ValueError as error:
        raise TrainSigningError("the pinned public key is not a valid Ed25519 key") from error
    try:
        key.verify(bytes.fromhex(raw_signature), _message(content))
    except invalid_signature as error:
        raise TrainSigningError(
            "the signature of the train does not match its content and the pinned key: the file was changed or signed by someone else"
        ) from error


def read_verified(train_path: Path, public_key: str | None) -> str:
    """The text of the train, read once, after checking that exact content against `<train>.sig` and the pinned key."""
    try:
        with train_path.open("rb") as handle:
            content = handle.read(MAX_TRAIN_BYTES + 1)
    except OSError as error:
        raise TrainSigningError(f"cannot read the train {train_path}: {error.strerror or error}") from error
    if len(content) > MAX_TRAIN_BYTES:
        raise TrainSigningError("the train file is too large")
    verify_train_bytes(content, signature_path(train_path), public_key)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise TrainSigningError("the train is not valid UTF-8") from error


def default_key_dir() -> Path:
    """Where the keys of the family live: the user's own folder, never a repository."""
    return Path.home() / ".hydra-umc-keys"


def generate_train_keypair(directory: Path, name: str = "hydra_train") -> tuple[Path, Path]:
    """Make a new Ed25519 pair for the version trains: `<name>.key` (private, 64 hex characters, owner only) and
    `<name>.pub` (public, 64 hex characters). Never overwrites a file; the private key is never printed or returned."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name) or name.startswith("."):
        raise TrainSigningError("the name of the key may only hold letters, digits, dot, dash and underscore")
    ed25519, _ = _ed25519()
    private_path, public_path = directory / f"{name}.key", directory / f"{name}.pub"
    try:
        already_there = private_path.exists() or public_path.exists()
    except OSError as error:  # a parent that is a file, a name the system refuses
        raise TrainSigningError(f"the keys cannot be written in {directory}") from error
    if already_there:
        raise TrainSigningError(f"{private_path.name} or {public_path.name} already exists in {directory}: nothing was overwritten")
    from cryptography.hazmat.primitives import serialization

    private = ed25519.Ed25519PrivateKey.generate()
    seed = private.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    ).hex()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(seed + "\n")
        public_path.write_text(public + "\n", encoding="utf-8")
    except OSError as error:
        private_path.unlink(missing_ok=True)
        raise TrainSigningError(f"the keys cannot be written in {directory}") from error
    return private_path, public_path
