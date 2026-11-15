# =============================================================================
# HYDRA-UMC-UPDATER - Applying a signed image delta to the inactive slot: image_delta.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Rebuilds the image of a signed release from the image of the running slot and a signed delta, so an A/B update moves only the blocks that changed.

The image builder publishes, next to the release, a folder with `delta.json` (format `hydra-image-delta/1`: the size and SHA-256 of the base and of the target, the block size, the
list of blocks), `delta.bin` (the bytes of the blocks that are new) and `delta.json.sig`, an Ed25519 signature over a domain tag of its own plus the SHA-256 of the exact bytes of
`delta.json`. This module reads the running image (the BASE) and writes only the image of the INACTIVE slot; it never touches the base, never switches the slot and never receives a
private key. Nothing is written until everything has held:

1. the use of deltas is switched on (off by default: `image_delta`, `HYDRA_UMC_UPDATER_IMAGE_DELTA`);
2. the release (`release.json` and its signature) verifies against the trusted keys, exactly as `image verify` does;
3. the delta verifies against the same keys (its own domain, so a release or a profile can never pass as a delta), and its TARGET is the image of the release (size and SHA-256);
4. the base is the image the delta was made from (size and SHA-256) and `delta.bin` matches its record;
5. the image is rebuilt in a staging folder, block by block with every range checked, and the rebuilt image verifies against the release (name, size, SHA-256);
6. only then it replaces the image of the inactive slot, in one rename.

Fail closed: any doubt rejects with a reason (`ImageDeltaError.code`, translated by the command) and leaves the output folder as it was. The format and the domain are those of the delta
commands of the image builder (`delta-create`, `delta-apply`). Evidence: simulator (synthetic images and ephemeral keys); not run against a real image or the device."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import image_release
from .image_release import ImageReleaseError, TrustedKeys, file_sha256

FORMAT = "hydra-image-delta/1"
RECORD = "delta.json"
DATA = "delta.bin"
DOMAIN = b"hydra-umc-os-rebuilder-delta/1\n"
MIN_BLOCK = 512
MAX_BLOCK = 16 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024 * 1024


class ImageDeltaError(ImageReleaseError):
    """A delta that is refused. Same shape as `ImageReleaseError`; its codes are keys of the translations `imgdelta_<code>` (or `imgrel_<code>` for the ones of the release)."""


@dataclass
class ImageDeltaResult:
    version: str
    image: str
    sha256: str
    size: int
    copied_bytes: int
    new_bytes: int
    checked: list[str] = field(default_factory=list)


def _bad(code: str, english: str, **params: object) -> ImageDeltaError:
    return ImageDeltaError(code, english, **params)


def _load_record(store: Path, keys: TrustedKeys) -> dict[str, Any]:
    record, sig = store / RECORD, store / (RECORD + ".sig")
    if not record.is_file() or not sig.is_file():
        raise _bad("missing", f"{store} does not hold {RECORD} and its signature", name=RECORD)
    if record.stat().st_size > MAX_RECORD_BYTES:
        raise _bad("bad_record", f"{RECORD} is too large")
    content = record.read_bytes()
    try:
        raw = sig.read_text(encoding="ascii").strip()
        signature = bytes.fromhex(raw)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise _bad("signature", f"the signature of {RECORD} cannot be read") from error
    if len(signature) != 64:
        raise _bad("signature", f"the signature of {RECORD} is not an Ed25519 signature")
    ed25519, invalid = image_release._ed25519()
    message = DOMAIN + hashlib.sha256(content).hexdigest().encode("ascii")
    verified = False
    for key in keys.active:
        try:
            ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(signature, message)
        except (ValueError, invalid):
            continue
        verified = True
        break
    if not verified:
        raise _bad("signature", f"the signature of {RECORD} does not verify against any trusted key")
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise _bad("bad_record", f"{RECORD} is not valid JSON") from error
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise _bad("bad_record", f"{RECORD} is not a {FORMAT} file")
    _check_record(data)
    return data


def _check_record(data: dict[str, Any]) -> None:
    sha = image_release._SHA256
    for part in ("base", "target", "data"):
        entry = data.get(part)
        if not isinstance(entry, dict) or not isinstance(entry.get("size"), int) or isinstance(entry["size"], bool) or entry["size"] < 0 or not isinstance(entry.get("sha256"), str) or not sha.match(entry["sha256"]):
            raise _bad("bad_record", f"the field {part!r} of {RECORD} is missing or malformed")
    block = data.get("block_size")
    if not isinstance(block, int) or isinstance(block, bool) or not MIN_BLOCK <= block <= MAX_BLOCK:
        raise _bad("bad_record", "the block size of the delta is out of range")
    blocks = data.get("blocks")
    if not isinstance(blocks, list):
        raise _bad("bad_record", "the block list of the delta is missing")
    for item in blocks:
        if not (isinstance(item, list) and len(item) == 3 and item[0] in ("c", "l") and all(isinstance(n, int) and not isinstance(n, bool) for n in item[1:])):
            raise _bad("bad_record", "a block of the delta is malformed")


def _rebuild(base: Path, payload: Path, data: dict[str, Any], output: Path) -> int:
    """Write the target to `output` from the blocks of the record; every range is checked before it is read. Returns the bytes copied from the base."""
    block = int(data["block_size"])
    base_size = int(data["base"]["size"])
    literal_size = int(data["data"]["size"])
    copied = 0
    result = hashlib.sha256()
    written = 0
    with base.open("rb") as source, payload.open("rb") as literal, output.open("wb") as out:
        for op, where, length in data["blocks"]:
            if length <= 0 or length > block:
                raise _bad("block", "a block of the delta has a length outside the block size")
            if op == "c":
                start = where * block
                if where < 0 or start >= base_size or start + length > base_size:
                    raise _bad("block", "a block of the delta points outside the base image")
                source.seek(start)
                chunk = source.read(length)
                copied += length
            else:
                if where < 0 or where + length > literal_size:
                    raise _bad("block", "a block of the delta points outside its data")
                literal.seek(where)
                chunk = literal.read(length)
            if len(chunk) != length:
                raise _bad("block", "a block of the delta is shorter than the record says")
            out.write(chunk)
            result.update(chunk)
            written += length
    if written != data["target"]["size"] or result.hexdigest() != data["target"]["sha256"]:
        raise _bad("result", "the rebuilt image does not match the target of the delta")
    return copied


def apply_delta(
    release: Path,
    store: Path,
    base: Path,
    out_dir: Path,
    keys: TrustedKeys,
    *,
    enabled: bool,
) -> ImageDeltaResult:
    """Rebuild the image of `release` from `base` and the delta in `store` into `out_dir` (the inactive slot). Writes nothing unless every check holds."""
    if not enabled:
        raise _bad("disabled", "the use of image deltas is switched off")
    content, data_release = image_release._read_manifest(release)
    image_release.verify_signature(release, content, keys)
    image_release._check_fields(data_release)
    record = _load_record(store, keys)
    if record["target"]["size"] != data_release["size"] or record["target"]["sha256"] != data_release["sha256"]:
        raise _bad("not_release", "the delta does not build the image of this release (size or SHA-256 of the target)")
    if not base.is_file():
        raise _bad("base", f"the base image {base.name} cannot be read", name=base.name)
    if base.stat().st_size != record["base"]["size"] or file_sha256(base) != record["base"]["sha256"]:
        raise _bad("base", "the base image is not the one this delta was made from (size or SHA-256)", name=base.name)
    payload = store / DATA
    if not payload.is_file() or payload.stat().st_size != record["data"]["size"] or file_sha256(payload) != record["data"]["sha256"]:
        raise _bad("data", f"{DATA} does not match its record (size or SHA-256)", name=DATA)
    name = data_release["image"]
    if out_dir.resolve() == base.resolve().parent and name == base.name:
        raise _bad("same_slot", "the output would replace the base image: the delta is written to the other slot")
    out_dir.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".delta-stage-", dir=out_dir))
    try:
        staged = stage / name
        copied = _rebuild(base, payload, record, staged)
        image_release.verify_release(release, staged, keys)
        os.replace(staged, out_dir / name)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return ImageDeltaResult(data_release["version"], str(out_dir / name), data_release["sha256"], int(data_release["size"]), copied, int(record["data"]["size"]), ["signature", "delta", "base", "data", "result", "sha256"])
