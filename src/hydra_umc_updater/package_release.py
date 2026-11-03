# =============================================================================
# HYDRA-UMC-UPDATER - Signed packages of a release: package_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Verifies and installs the signed package of a release.

A package is `<project>-<version>.tgz` with its hash `<project>-<version>.tgz.sha256` and its signature `<project>-<version>.tgz.sig`: the
Ed25519 signature, by the key of the releases of HYDRA-UMC, of the text `hydra-pc-pkg/1|<project>|<version>|<sha256 of the package>`. Binding the
project and the version to the hash means a signed package of another project, or of an older version, cannot be presented as this one or as the
newest. The same key and the same scheme as the packages of the device (`hydra-pkg/1` of HYDRA-UMC-OS) with their own prefix, so a signature made
for one kind of package is never valid for the other.

The public key of the releases is pinned here (`RELEASES_PUBLIC_KEY`); it is a public key and the private one is never in this program. By default
a package without a valid signature is refused with a reason. The saved setting `require_signed_packages` (default on; a damaged settings file
counts as on) lets a person who runs their own packages accept a package that has its `.sha256` but no `.sig`; a signature that is present and
wrong is refused whatever the setting says.

Installing writes next to the final place: the package is extracted into a staging folder (only regular files and folders, only paths that stay
inside it, bounded size), its manifest must name the version of the package, and then the previous folder is renamed aside (kept as a backup,
never deleted) and the staging folder takes its place. A version that is not newer than the installed one is refused.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from . import github_client, settings
from .release_channel import ReleaseInfo

#: Public key of the releases of HYDRA-UMC (raw Ed25519, 64 hexadecimal characters). Public by nature.
RELEASES_PUBLIC_KEY = "1228393cae6cb9fba1d98e300446956de2bc1e9c5b59cc58035a65dbcf4f2331"
MESSAGE_PREFIX = "hydra-pc-pkg/1"
REQUIRE_SIGNED_PACKAGES_ENV = "HYDRA_UMC_UPDATER_REQUIRE_SIGNED_PACKAGES"
NAME_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9-]{0,99})-(\d+\.\d+\.\d+(?:\.\d+)?)\.tgz$")
MAX_PACKAGE_BYTES = 200 * 1024 * 1024
MAX_UNPACKED_BYTES = 800 * 1024 * 1024
MAX_MEMBERS = 50_000
MAX_SMALL_FILE_BYTES = 4096
MANIFEST_FILE = "hydra-umc.project.json"
_SHA256_LINE = re.compile(r"^([0-9a-fA-F]{64})(?:\s|$)")
_HEX_SIGNATURE = re.compile(r"^[0-9a-fA-F]{128}$")
_HEX_KEY = re.compile(r"^[0-9a-f]{64}$")

Downloader = Callable[[str, Path, int], None]


class PackageError(ValueError):
    """A package that is refused. `code` names the reason (a key of the translations: `pkg_<code>`), `params` fill its blanks."""

    def __init__(self, code: str, english: str, **params: object) -> None:
        super().__init__(english)
        self.code = code
        self.params = params


@dataclass(frozen=True)
class PackageResult:
    name: str
    version: str
    sha256: str
    signed: bool
    fingerprint: str


def signature_required() -> bool:
    """On unless the saved settings say off; the environment variable can only turn it on."""
    if os.environ.get(REQUIRE_SIGNED_PACKAGES_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return settings.get_require_signed_packages()


def fingerprint(public_key_hex: str) -> str:
    digest = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:16]
    return ":".join(digest[i : i + 4] for i in range(0, 16, 4))


def package_message(name: str, version: str, sha256_hex: str) -> bytes:
    return f"{MESSAGE_PREFIX}|{name}|{version}|{sha256_hex}".encode("utf-8")


def _ed25519() -> tuple[object, type[Exception]]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as error:
        raise PackageError("no_crypto", 'verifying a signature needs the "cryptography" package: pip install "hydra-umc-updater[signing]"') from error
    return ed25519, InvalidSignature


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_small(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_SMALL_FILE_BYTES:
            return None
        return path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None


def check_members(package: Path) -> int:
    """Only regular files and folders below the root of the package: nothing can be written outside the target. Returns the unpacked size."""
    total = 0
    try:
        with tarfile.open(package, "r:gz") as tar:
            for count, member in enumerate(tar, start=1):
                name = member.name
                if count > MAX_MEMBERS:
                    raise PackageError("too_big", "the package holds too many files")
                if not (member.isreg() or member.isdir()):
                    raise PackageError("member_bad", f"{name} is not a regular file or a folder", member=name)
                parts = Path(name).parts
                if (
                    not name or name.startswith(("/", "\\")) or "\\" in name or ".." in parts
                    or re.match(r"^[A-Za-z]:", name) or any(part == ".git" for part in parts)
                ):
                    raise PackageError("member_bad", f"{name} would be written outside the target", member=name)
                total += max(member.size, 0)
                if total > MAX_UNPACKED_BYTES:
                    raise PackageError("too_big", "the package unpacks to more than the allowed size")
    except (tarfile.TarError, OSError, EOFError) as error:
        raise PackageError("unreadable", f"the archive cannot be read: {error}", name=package.name) from error
    return total


def verify_package(
    package: Path,
    *,
    public_key_hex: str | None = None,
    require_signature: bool | None = None,
) -> PackageResult:
    """Everything that must hold before a package is touched: name, size, `.sha256`, signature (by default required) and members. Reads only."""
    public_key_hex = public_key_hex or RELEASES_PUBLIC_KEY  # looked up now: the pinned key is a constant of this module
    match = NAME_PATTERN.match(package.name)
    if not match:
        raise PackageError("name_bad", f"{package.name} is not named <project>-<version>.tgz", name=package.name)
    name, version = match.groups()
    if not _HEX_KEY.match(public_key_hex):
        raise PackageError("sig_bad", "the pinned public key is not a raw Ed25519 key")
    try:
        if not package.is_file() or package.stat().st_size > MAX_PACKAGE_BYTES:
            raise OSError
        digest = file_sha256(package)
    except OSError as error:
        raise PackageError("unreadable", f"the package {package.name} cannot be read or is too large", name=package.name) from error
    sha_text = _read_small(package.with_name(package.name + ".sha256"))
    sha_match = _SHA256_LINE.match(sha_text) if sha_text else None
    if sha_match is None:
        raise PackageError("sha256_missing", "the .sha256 of the package is missing or unreadable")
    if sha_match.group(1).lower() != digest:
        raise PackageError("sha256_bad", "the hash does not match the package: it was changed after it was published")
    needs_signature = signature_required() if require_signature is None else require_signature
    sig_text = _read_small(package.with_name(package.name + ".sig"))
    signed = False
    if sig_text is None:
        if needs_signature:
            raise PackageError("sig_missing", "the .sig is missing: an unsigned package is never installed")
    else:
        if not _HEX_SIGNATURE.match(sig_text):
            raise PackageError("sig_bad", "the .sig is not an Ed25519 signature in hexadecimal")
        ed25519, invalid = _ed25519()
        try:
            ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(  # type: ignore[attr-defined]
                bytes.fromhex(sig_text), package_message(name, version, digest)
            )
        except (ValueError, invalid) as error:
            raise PackageError("sig_bad", "the signature is not valid for this project, this version and this hash") from error
        signed = True
    check_members(package)
    return PackageResult(name, version, digest, signed, fingerprint(public_key_hex))


def _version_tuple(text: str) -> tuple[int, ...]:
    parts = [int(part) for part in text.split(".")]
    return tuple(parts + [0] * (4 - len(parts)))


def _manifest_version(folder: Path) -> str | None:
    try:
        data = json.loads((folder / MANIFEST_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+(\.\d+)?", version) else None


def _extract(package: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    root = destination.resolve()
    with tarfile.open(package, "r:gz") as tar:
        for member in tar:
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise PackageError("member_bad", f"{member.name} would be written outside the target", member=member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            if source is None:
                raise PackageError("member_bad", f"{member.name} cannot be read", member=member.name)
            with source, target.open("wb") as out:
                shutil.copyfileobj(source, out)
            if member.mode & 0o111 and os.name != "nt":
                target.chmod(0o755)


def install_package(package: Path, workspace_root: Path, *, public_key_hex: str | None = None, require_signature: bool | None = None) -> PackageResult:
    """Verify the package, extract it next to its place and put it there; the previous folder is kept as `<project>.backup-<id>`."""
    result = verify_package(package, public_key_hex=public_key_hex, require_signature=require_signature)
    final = workspace_root / result.name
    staging = workspace_root / f".{result.name}.package-{uuid4().hex}"
    try:
        _extract(package, staging)
        extracted = _manifest_version(staging)
        if extracted != result.version:
            raise PackageError("manifest_bad", f"the manifest inside the package says {extracted or 'nothing usable'}, not {result.version}")
        installed = _manifest_version(final) if final.is_dir() else None
        if installed is not None and _version_tuple(result.version) <= _version_tuple(installed):
            raise PackageError("not_newer", f"{result.version} is not newer than the {installed} installed", version=result.version, installed=installed)
        if final.exists() and installed is None and not (final / ".git").exists():
            raise PackageError("install_failed", f"{final} exists and is not an installation this updater can replace", detail=str(final))
        try:
            if final.exists():
                final.rename(workspace_root / f"{result.name}.backup-{uuid4().hex[:8]}")
            staging.rename(final)
        except OSError as error:
            raise PackageError("install_failed", f"could not put the package in place: {error}", detail=str(error)) from error
    except (OSError, tarfile.TarError) as error:
        raise PackageError("install_failed", f"the package could not be extracted: {error}", detail=str(error)) from error
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return result


def download_to_file(url: str, destination: Path, limit: int) -> None:
    """Download an https address to a file, refusing more than `limit` bytes."""
    if not url.startswith("https://"):
        raise OSError("only https addresses are downloaded")
    request = urllib.request.Request(url, headers={"User-Agent": github_client.USER_AGENT})
    written = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as out:  # noqa: S310 - https only, checked above
        for chunk in iter(lambda: response.read(1 << 20), b""):
            written += len(chunk)
            if written > limit:
                raise OSError("the download is larger than allowed")
            out.write(chunk)


def fetch_release_package(info: ReleaseInfo, into: Path, *, download: Downloader | None = None) -> Path:
    """Download the package of a release and its `.sha256` and `.sig` (when it has one) into `into`; returns the package path."""
    download = download or download_to_file
    prefix = "https://github.com/"
    wanted = f"{info.repo}-{info.version}.tgz"
    if wanted not in info.assets:
        raise PackageError("no_asset", f"the release {info.tag} of {info.repo} has no package {wanted}", version=info.version)
    for asset, limit in ((wanted, MAX_PACKAGE_BYTES), (wanted + ".sha256", MAX_SMALL_FILE_BYTES), (wanted + ".sig", MAX_SMALL_FILE_BYTES)):
        url = info.assets.get(asset)
        if url is None:
            continue  # a missing .sha256 or .sig is judged by verify_package, with its own reason
        if not url.startswith(prefix):
            raise PackageError("download_failed", f"{asset} is not served from GitHub", name=asset)
        try:
            download(url, into / asset, limit)
        except (OSError, ValueError) as error:
            raise PackageError("download_failed", f"{asset} could not be downloaded: {error}", name=asset) from error
    return into / wanted
