# =============================================================================
# HYDRA-UMC-UPDATER - Signed bundles of compiled models: model_bundle.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Verifies and installs the signed bundle of compiled models of HYDRA-UMC-DETECTION-HEF on the machine that runs the detection service.

A bundle is a zip file made by `make_bundle` of that project: `bundle.json` (the format, 1, and the SHA-256 of every other member), `registry.json` with its
detached Ed25519 signature `registry.json.sig` (the signature is over the exact bytes of the registry, written as 128 hexadecimal digits) and the `.hef` files
under `models/`, at the paths the registry gives them. This module reads that format and does not import the detection service, so the updater keeps no
dependency on it; `tests/test_model_bundle.py` builds bundles with the real `make_bundle` when the checkout of that project sits next to this one and checks that
both sides accept and refuse the same things.

Nothing is believed that was not checked, and the whole bundle is checked before the first file is written:

* it is off unless the operator turns it on (the `model_bundles` setting or HYDRA_UMC_UPDATER_MODEL_BUNDLES=1), and it needs the public key of the owner of the
  registry: an unsigned bundle is not an update;
* member names are checked (no absolute path, no `..`, no backslash, only the four kinds above), their number and total size are limited, every member must have
  the SHA-256 that `bundle.json` lists, and nothing may be in the zip that `bundle.json` does not list;
* the signature of `registry.json` must verify with the public key, and every `.hef` must have the SHA-256 that its registry entry records;
* a model that would go to an older version than the machine has, or disappear from the registry, is refused unless the downgrade is asked for;
* only then are the `.hef` files put in place (each under a temporary name and renamed), the previous registry and signature kept as `.prev`, and the new
  registry and signature renamed over the old ones, all under the lock the detection service uses for its registry.
"""
from __future__ import annotations

import binascii
import contextlib
import hashlib
import json
import os
import re
import shutil
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from . import package_release, settings
from .package_release import PackageError, fingerprint

MODEL_BUNDLES_ENV = "HYDRA_UMC_UPDATER_MODEL_BUNDLES"
BUNDLE_FORMAT = 1
MANIFEST = "bundle.json"
REGISTRY = "registry.json"
SIGNATURE = REGISTRY + ".sig"
PREVIOUS_SUFFIX = ".prev"
MAX_MEMBERS = 1000
MAX_TOTAL_BYTES = 512 * 1024 * 1024
CHANNELS = ("stable", "canary")
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class BundleResult:
    models: tuple[str, ...]
    files: tuple[str, ...]
    fingerprint: str


def enabled() -> bool:
    """Off unless the saved settings say so or the environment variable is set to a true word (the environment can switch it on, never off)."""
    if os.environ.get(MODEL_BUNDLES_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return settings.get_model_bundles()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _member_ok(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name or "\x00" in name or len(name) > 300:
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") or part.endswith(":") for part in parts):
        return False
    if name in (MANIFEST, REGISTRY, SIGNATURE):
        return True
    return parts[0] == "models" and len(parts) >= 2


def read_public_key(path: Path) -> bytes:
    """32 bytes from a file that holds them raw or as 64 hexadecimal digits. The key is public, but a file that is neither is refused with a reason."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise PackageError("models_key_bad", f"The public key file {path} cannot be read: {exc}", name=str(path)) from exc
    if len(data) == 32:
        return data
    try:
        key = binascii.unhexlify(data.decode("ascii", errors="replace").strip())
    except (binascii.Error, ValueError):
        key = b""
    if len(key) != 32:
        raise PackageError("models_key_bad", f"The public key file {path} is not a 32-byte Ed25519 key.", name=str(path))
    return key


def _read_members(path: Path) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackageError("models_unreadable", f"{path.name} is not a readable bundle: {exc}", name=path.name, detail=str(exc)) from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS or sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
            raise PackageError("models_limits", "The bundle holds too many members or would unpack to more than the allowed size.")
        names = [info.filename for info in infos]
        if len(set(names)) != len(names):
            raise PackageError("models_member_bad", "The bundle repeats a member name.", member="(repeated)")
        for name in names:
            if not _member_ok(name):
                raise PackageError("models_member_bad", f"The bundle has a member that is not allowed: {name!r}", member=name)
        members: dict[str, bytes] = {}
        for info in infos:
            try:
                with archive.open(info) as handle:
                    data = handle.read(info.file_size + 1)
            except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
                raise PackageError("models_unreadable", f"{path.name} is not a readable bundle: {exc}", name=path.name, detail=str(exc)) from exc
            if len(data) != info.file_size:
                raise PackageError("models_hash_bad", f"{info.filename} is not the size the bundle announces.", member=info.filename)
            members[info.filename] = data
    return members


def _check_listing(members: dict[str, bytes]) -> None:
    if MANIFEST not in members:
        raise PackageError("models_format_bad", "The bundle has no bundle.json or it does not list its files with format 1.")
    try:
        manifest = json.loads(members.pop(MANIFEST).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise PackageError("models_format_bad", "The bundle has no bundle.json or it does not list its files with format 1.") from exc
    listed = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(manifest, dict) or manifest.get("format") != BUNDLE_FORMAT or not isinstance(listed, dict):
        raise PackageError("models_format_bad", "The bundle has no bundle.json or it does not list its files with format 1.")
    if set(listed) != set(members):
        different = sorted(set(listed) ^ set(members))[0]
        raise PackageError("models_hash_bad", f"{different} is listed in only one of the zip and bundle.json.", member=different)
    for name, data in members.items():
        if listed[name] != _sha256(data):
            raise PackageError("models_hash_bad", f"{name} does not match the SHA-256 in bundle.json.", member=name)
    for needed in (REGISTRY, SIGNATURE):
        if needed not in members:
            raise PackageError("models_format_bad", f"The bundle has no {needed}.")


def _verify_signature(registry: bytes, signature_text: bytes, public_key: bytes) -> None:
    ed25519, invalid_signature = package_release._ed25519()
    try:
        signature = binascii.unhexlify(signature_text.decode("ascii").strip())
    except (UnicodeDecodeError, binascii.Error, ValueError):
        signature = b""
    try:
        key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)  # type: ignore[attr-defined]
        if len(signature) != 64:
            raise invalid_signature()
        key.verify(signature, registry)
    except invalid_signature as exc:
        raise PackageError("models_sig_bad", "The signature of the registry in the bundle does not verify with this public key.") from exc


@dataclass(frozen=True)
class _Entry:
    name: str
    version: tuple[int, int, int]
    version_text: str
    channel: str
    hef_path: str
    sha256: str


def _parse_registry(registry: bytes) -> list[_Entry]:
    try:
        raw = json.loads(registry.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise PackageError("models_registry_bad", f"The registry in the bundle cannot be read: {exc}", detail=str(exc)) from exc
    if not isinstance(raw, list):
        raise PackageError("models_registry_bad", "The registry in the bundle must be a JSON array of entries.", detail="not an array")
    entries = []
    for index, item in enumerate(raw):
        fields = {key: item.get(key) for key in ("name", "version", "hef_path", "sha256")} if isinstance(item, dict) else {}
        channel = item.get("channel", "stable") if isinstance(item, dict) else None
        version = _VERSION.match(fields.get("version") or "") if isinstance(fields.get("version"), str) else None
        if (not all(isinstance(value, str) and value for value in fields.values()) or version is None or channel not in CHANNELS
                or not _SHA256.match(fields["sha256"])):
            raise PackageError("models_registry_bad", f"Entry {index} of the registry in the bundle is not a model entry.", detail=f"entry {index}")
        entries.append(_Entry(fields["name"], tuple(int(part) for part in version.groups()), fields["version"], channel,
                             fields["hef_path"].replace("\\", "/"), fields["sha256"].lower()))
    return entries


def _newest(entries: list[_Entry]) -> dict[tuple[str, str], tuple[int, int, int]]:
    best: dict[tuple[str, str], tuple[int, int, int]] = {}
    for entry in entries:
        key = (entry.name, entry.channel)
        if key not in best or entry.version > best[key]:
            best[key] = entry.version
    return best


def _check(bundle: Path, public_key_file: Path | None) -> tuple[dict[str, bytes], list[_Entry], str]:
    """Everything that can be refused without looking at what is installed; reads only."""
    if public_key_file is None:
        raise PackageError("models_needs_key", "A model bundle is only accepted with the public key of the owner of the registry (--public-key).")
    public_key = read_public_key(public_key_file)
    members = _read_members(Path(bundle))
    _check_listing(members)
    _verify_signature(members[REGISTRY], members[SIGNATURE], public_key)
    entries = _parse_registry(members[REGISTRY])
    by_path = {entry.hef_path: entry for entry in entries}
    for name, data in members.items():
        if not name.startswith("models/"):
            continue
        entry = by_path.get(name[len("models/"):])
        if entry is None:
            raise PackageError("models_hef_bad", f"{name} is in the bundle but no entry of the registry points at it.", member=name)
        if _sha256(data) != entry.sha256:
            raise PackageError("models_hef_bad", f"{name} does not have the SHA-256 that its registry entry records.", member=name)
    return members, entries, fingerprint(public_key.hex())


def verify_bundle(bundle: Path, public_key_file: Path | None) -> BundleResult:
    """Checks a bundle without installing anything (no switch needed: it only reads)."""
    members, entries, finger = _check(bundle, public_key_file)
    return BundleResult(tuple(sorted(f"{e.name} {e.version_text}" for e in entries)), tuple(sorted(n for n in members if n.startswith("models/"))), finger)


@contextlib.contextmanager
def _registry_lock(registry: Path, timeout: float = 10.0) -> Iterator[None]:
    """The same lock file the detection service takes around a change of its registry (`<registry>.lock`, created exclusively)."""
    lock_path = registry.with_name(registry.name + ".lock")
    deadline = time.monotonic() + timeout
    while True:
        try:
            handle = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise PackageError("models_install_failed", f"{lock_path} is held by another process.", detail=f"{lock_path.name} is held by another process") from None
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(handle)
        with contextlib.suppress(OSError):
            lock_path.unlink()


def _replace(destination: Path, data: bytes) -> None:
    part = destination.with_name(destination.name + ".part")
    part.write_bytes(data)
    os.replace(part, destination)


def install_bundle(bundle: Path, registry_path: Path, models_dir: Path, public_key_file: Path | None, *, allow_downgrade: bool = False,
                   require_enabled: bool = True) -> BundleResult:
    """Checks the bundle in full and puts it in place. Raises PackageError before touching anything when a check fails; a failure while writing is reported
    as `models_install_failed` and the previous registry and signature (kept as `.prev`) are the way back."""
    if require_enabled and not enabled():
        raise PackageError("models_off", f"Installing model bundles is off: set {MODEL_BUNDLES_ENV}=1 or `model_bundles: true` in the settings.")
    members, entries, finger = _check(bundle, public_key_file)
    registry_path, models_dir = Path(registry_path), Path(models_dir)
    root = models_dir.resolve()
    targets: dict[str, Path] = {}
    for name in members:
        if name.startswith("models/"):
            target = (models_dir / name[len("models/"):]).resolve()
            if not target.is_relative_to(root):
                raise PackageError("models_member_bad", f"{name} would be written outside {models_dir}.", member=name)
            targets[name] = target
    try:
        with _registry_lock(registry_path):
            if registry_path.is_file() and not allow_downgrade:
                old = _newest(_parse_registry_file(registry_path))
                new = _newest(entries)
                for key, version in new.items():
                    if key in old and version < old[key]:
                        raise PackageError("models_downgrade", f"{key[0]} ({key[1]}) would go from {_dotted(old[key])} to {_dotted(version)}.",
                                           model=key[0], channel=key[1], installed=_dotted(old[key]), version=_dotted(version))
                lost = sorted(key for key in old if key not in new)
                if lost:
                    raise PackageError("models_lost", f"The new registry no longer lists {lost[0][0]} ({lost[0][1]}).", model=lost[0][0], channel=lost[0][1])
            installed = []
            for name, target in targets.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                _replace(target, members[name])
                installed.append(name)
            signature_path = registry_path.with_name(registry_path.name + ".sig")
            for current in (registry_path, signature_path):
                if current.is_file():
                    shutil.copy2(current, current.with_name(current.name + PREVIOUS_SUFFIX))
            _replace(registry_path, members[REGISTRY])
            _replace(signature_path, members[SIGNATURE])
    except OSError as exc:
        raise PackageError("models_install_failed", f"The bundle could not be put in place: {exc}", detail=str(exc)) from exc
    return BundleResult(tuple(sorted(f"{e.name} {e.version_text}" for e in entries)), tuple(sorted(installed)), finger)


def _parse_registry_file(path: Path) -> list[_Entry]:
    try:
        return _parse_registry(path.read_bytes())
    except OSError as exc:
        raise PackageError("models_registry_bad", f"The installed registry cannot be read: {exc}", detail=str(exc)) from exc


def _dotted(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)

