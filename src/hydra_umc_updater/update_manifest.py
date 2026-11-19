# =============================================================================
# HYDRA-UMC-UPDATER - Asymmetric signature of the update manifest: update_manifest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Ed25519 signature of an `UpdateManifest`, the list of keys that are trusted to make it, and the rule that decides whether a manifest passes.

What is signed: the manifest WITHOUT its `signature` field, as canonical JSON (keys sorted, no spaces, UTF-8). `signature_alg` and `key_id` are inside what is
signed, so neither can be removed or changed without breaking the signature.

Which keys count: a list of PUBLIC keys (`keys_from_json`). Each key has a `key_id` (the first eight bytes of the SHA-512 of the key, which the loader checks),
a `state` (`current`, `next`, `retired` or `revoked`) and an optional validity window (`not_before`, `not_after`). A key rotates by being added as `next` with a
`not_before`, used from then on, and moved to `retired` with a `not_after` (a grace period for manifests published before the rotation); `revoked` never counts.
A list with a key whose `key_id` does not match its public key, or with two entries for one `key_id`, is refused whole.

The rule (`verify_manifest`), with the switch `require_asymmetric_signature` (off by default while the ecosystem moves over):
- a manifest WITH an Ed25519 signature is always checked, whatever the switch says: a bad signature, an unknown, revoked, not yet valid or expired key is refused. A
  signature that is present is never quietly treated as a legacy manifest;
- a manifest WITHOUT one (a legacy manifest, protected only by the hash and the transport) passes while the switch is off, labelled `legacy`, and is refused as
  `downgrade_refused` when the switch is on.

This module is the rule of HYDRA-UMC-SDK `hydra_umc_sdk.manifest_signing` (docs/MANIFEST_SIGNING.md there), kept here so the updater stays free of
dependencies; tests/fixtures/manifest-signing-vectors.json is a copy of the SDK vectors and both must give the same verdicts.
The signing function here exists for tests and for tools that already hold a seed; the seed of an official key is never kept in a repository. The verifier is a
plain RFC 8032 implementation in the standard library (it handles only public data), so the updater stays free of dependencies.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

SIGNATURE_ALG = "ed25519"
KEY_STATES = ("current", "next", "retired", "revoked")
CODES = (
    "ok",
    "legacy",
    "downgrade_refused",
    "malformed",
    "bad_signature",
    "unknown_key",
    "key_revoked",
    "key_not_yet_valid",
    "key_expired",
)
_HEX_SIGNATURE = re.compile(r"[0-9a-f]{128}")
_HEX_KEY = re.compile(r"[0-9a-f]{64}")
_HEX_KEY_ID = re.compile(r"[0-9a-f]{16}")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

# --- Ed25519, RFC 8032 section 6 (public data only) ---------------------------------------------------------------------------------
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


def _recover_x(y: int, sign: int) -> int | None:
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _I % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


_GY = 4 * _inv(5) % _P
_GX = _recover_x(_GY, 0) or 0
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _add(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    aa = (a[1] - a[0]) * (b[1] - b[0]) % _P
    bb = (a[1] + a[0]) * (b[1] + b[0]) % _P
    cc = 2 * a[3] * b[3] * _D % _P
    dd = 2 * a[2] * b[2] % _P
    e, f, g, h = bb - aa, dd - cc, dd + cc, bb + aa
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(scalar: int, point: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _compress(point: tuple[int, int, int, int]) -> bytes:
    zinv = _inv(point[2])
    x, y = point[0] * zinv % _P, point[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(data: bytes) -> tuple[int, int, int, int] | None:
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _hash_int(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little")


def _expand(seed: bytes) -> tuple[int, bytes]:
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], "little")
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, digest[32:]


def public_key_from_seed(seed: bytes) -> bytes:
    """The public key of a 32-byte seed (tests and tools only)."""
    if len(seed) != 32:
        raise ValueError("an Ed25519 seed is 32 bytes")
    return _compress(_mul(_expand(seed)[0], _G))


def sign(seed: bytes, message: bytes) -> bytes:
    """An Ed25519 signature (64 bytes) of `message` (tests and tools only; not constant time)."""
    scalar, prefix = _expand(seed)
    public = _compress(_mul(scalar, _G))
    r = _hash_int(prefix + message) % _Q
    point_r = _compress(_mul(r, _G))
    k = _hash_int(point_r + public + message) % _Q
    s = (r + k * scalar) % _Q
    return point_r + int.to_bytes(s, 32, "little")


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """True when `signature` is a valid Ed25519 signature of `message` under `public_key`; any wrong length or non-canonical value is False."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    point_a = _decompress(public_key)
    point_r = _decompress(signature[:32])
    if point_a is None or point_r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    k = _hash_int(signature[:32] + public_key + message) % _Q
    return _equal(_mul(s, _G), _add(point_r, _mul(k, point_a)))


# --- manifest, keys, rule -----------------------------------------------------------------------------------------------------------
def key_id_of(public_key: bytes) -> str:
    """The `key_id` of a public key: the first eight bytes of its SHA-512, as 16 lowercase hexadecimal digits."""
    return hashlib.sha512(public_key).digest()[:8].hex()


def canonical_message(manifest: dict[str, Any]) -> bytes:
    """What a manifest signature is made over: the manifest without `signature`, as canonical JSON."""
    body = {name: value for name, value in manifest.items() if name != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign_manifest(manifest: dict[str, Any], seed: bytes) -> dict[str, Any]:
    """The manifest with `signature_alg`, `key_id` and `signature` set (tests and tools only)."""
    signed = {name: value for name, value in manifest.items() if name != "signature"}
    signed["signature_alg"] = SIGNATURE_ALG
    signed["key_id"] = key_id_of(public_key_from_seed(seed))
    signed["signature"] = sign(seed, canonical_message(signed)).hex()
    return signed


class KeyListError(ValueError):
    """A list of trusted keys that cannot be used. The list is then refused whole: nothing is trusted from a damaged list."""


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    public: bytes
    state: str
    not_before: datetime | None = None
    not_after: datetime | None = None


def _moment(value: Any, name: str) -> datetime | None:
    if value is None:
        return None
    if not (isinstance(value, str) and _TIME.fullmatch(value)):
        raise KeyListError(f"{name} must be null or a UTC time such as 2030-01-01T00:00:00Z")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def keys_from_json(text: str) -> tuple[TrustedKey, ...]:
    """Reads the list of trusted keys: `{"schema": 1, "keys": [{"key_id", "public", "state", "not_before", "not_after"}]}`. Any fault refuses the whole list."""
    try:
        data = json.loads(text)
    except ValueError as error:
        raise KeyListError("the list of keys is not valid JSON") from error
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("keys"), list):
        raise KeyListError("the list of keys must be an object with schema 1 and a keys array")
    keys: list[TrustedKey] = []
    seen: set[str] = set()
    for entry in data["keys"]:
        if not isinstance(entry, dict) or set(entry) - {"key_id", "public", "state", "not_before", "not_after", "label"}:
            raise KeyListError("a key entry has a field that is not part of the list format")
        public_hex, key_id, state = entry.get("public"), entry.get("key_id"), entry.get("state")
        if not (isinstance(public_hex, str) and _HEX_KEY.fullmatch(public_hex)):
            raise KeyListError("public must be 64 lowercase hexadecimal digits")
        public = bytes.fromhex(public_hex)
        if not (isinstance(key_id, str) and _HEX_KEY_ID.fullmatch(key_id)) or key_id != key_id_of(public):
            raise KeyListError("key_id does not belong to the public key")
        if state not in KEY_STATES:
            raise KeyListError("state must be current, next, retired or revoked")
        if key_id in seen:
            raise KeyListError("a key_id appears twice")
        seen.add(key_id)
        keys.append(TrustedKey(key_id, public, state, _moment(entry.get("not_before"), "not_before"), _moment(entry.get("not_after"), "not_after")))
    return tuple(keys)


@dataclass(frozen=True)
class ManifestVerdict:
    accepted: bool
    code: str
    key_id: str | None = None

    @property
    def legacy(self) -> bool:
        return self.code == "legacy"


def _refuse(code: str, key_id: str | None = None) -> ManifestVerdict:
    return ManifestVerdict(False, code, key_id)


def verify_manifest(
    manifest: dict[str, Any],
    keys: tuple[TrustedKey, ...],
    now: datetime,
    *,
    require_asymmetric_signature: bool = False,
) -> ManifestVerdict:
    """Decides whether a manifest passes (see the module text). `now` must be timezone-aware."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not isinstance(manifest, dict):
        return _refuse("malformed")
    has_signature = "signature" in manifest
    alg = manifest.get("signature_alg")
    if not has_signature:
        # A legacy manifest. It never carries a signature algorithm either: one that names an algorithm without a signature is damaged.
        if alg is not None or "key_id" in manifest and manifest.get("key_id") is not None:
            return _refuse("malformed")
        return _refuse("downgrade_refused") if require_asymmetric_signature else ManifestVerdict(True, "legacy")
    signature, key_id = manifest["signature"], manifest.get("key_id")
    if alg != SIGNATURE_ALG or not (isinstance(signature, str) and _HEX_SIGNATURE.fullmatch(signature)):
        return _refuse("malformed")
    if not (isinstance(key_id, str) and _HEX_KEY_ID.fullmatch(key_id)):
        return _refuse("malformed")
    key = next((candidate for candidate in keys if candidate.key_id == key_id), None)
    if key is None:
        return _refuse("unknown_key", key_id)
    if key.state == "revoked":
        return _refuse("key_revoked", key_id)
    if key.not_before is not None and now < key.not_before:
        return _refuse("key_not_yet_valid", key_id)
    if key.not_after is not None and now >= key.not_after:
        return _refuse("key_expired", key_id)
    if not verify(key.public, canonical_message(manifest), bytes.fromhex(signature)):
        return _refuse("bad_signature", key_id)
    return ManifestVerdict(True, "ok", key_id)
