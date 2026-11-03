#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-UPDATER - tools/package_pc_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Pack a tagged project as the signed package that the updater installs on a PC, on the side of whoever publishes the releases.

    python tools/package_pc_release.py pack ../HYDRA-UMC-STUDIO --tag v0.1.2 --out dist-packages
    python tools/package_pc_release.py sign dist-packages/HYDRA-UMC-STUDIO-0.1.2.tgz
    python tools/package_pc_release.py pack ../HYDRA-UMC-STUDIO --tag v0.1.2 --out dist-packages --sign
    python tools/package_pc_release.py verify dist-packages/HYDRA-UMC-STUDIO-0.1.2.tgz

`pack` writes `<project>-<version>.tgz` (the files of the tag, as `git archive` gives them) and `<project>-<version>.tgz.sha256`; `sign` writes
`<project>-<version>.tgz.sig`, the Ed25519 signature of the text `hydra-pc-pkg/1|<project>|<version>|<sha256>`. The three files are uploaded to the
release of that tag. The signing key is read from `HYDRA_RELEASE_KEY` (a path to an unencrypted PKCS#8 PEM) or from
`~/.hydra-umc-keys/hydra_release_ed25519.pem`; it is never printed, never copied and never inside a repository, and nothing is signed unless its
public half is the key that the updater pins (`RELEASES_PUBLIC_KEY`). Needs the `cryptography` package.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hydra_umc_updater import package_release  # noqa: E402


def key_path() -> Path:
    given = os.environ.get("HYDRA_RELEASE_KEY")
    return Path(given) if given else Path.home() / ".hydra-umc-keys" / "hydra_release_ed25519.pem"


def load_private_key(path: Path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise SystemExit("the key file is not an Ed25519 private key")
    return key


def public_hex(private_key) -> str:
    from cryptography.hazmat.primitives import serialization

    return private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def pack(repo: Path, tag: str, out: Path) -> Path:
    """The files of `tag` of the repository at `repo` as `<project>-<version>.tgz`, with its `.sha256`."""
    version = tag[1:] if tag.startswith("v") else tag
    name = repo.resolve().name
    out.mkdir(parents=True, exist_ok=True)
    package = out / f"{name}-{version}.tgz"
    if not package_release.NAME_PATTERN.match(package.name):
        raise SystemExit(f"{package.name} is not a name the updater accepts")
    done = subprocess.run(["git", "archive", "--format=tar.gz", "-o", str(package), tag], cwd=repo, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git archive failed: {done.stderr.strip()}")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_name(package.name + ".sha256").write_text(f"{digest}  {package.name}\n", encoding="ascii", newline="\n")
    return package


def sign(package: Path, private_key=None) -> Path:
    """Write `<package>.sig`. Refuses a key that is not the pinned one and a `.sha256` that is not the hash of the file."""
    match = package_release.NAME_PATTERN.match(package.name)
    if not match:
        raise SystemExit(f"{package.name} is not named <project>-<version>.tgz")
    name, version = match.groups()
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    sha_file = package.with_name(package.name + ".sha256")
    if sha_file.is_file() and not sha_file.read_text(encoding="ascii").lower().startswith(digest):
        raise SystemExit("the .sha256 next to the package is not the hash of this file")
    if private_key is None:
        path = key_path()
        if not path.is_file():
            raise SystemExit(f"there is no signing key at {path} (HYDRA_RELEASE_KEY names another place)")
        private_key = load_private_key(path)
    if public_hex(private_key) != package_release.RELEASES_PUBLIC_KEY:
        raise SystemExit("the key that would sign is not the one the updater pins: the updater would refuse the package")
    target = package.with_name(package.name + ".sig")
    target.write_text(private_key.sign(package_release.package_message(name, version, digest)).hex() + "\n", encoding="ascii", newline="\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    pack_p = commands.add_parser("pack")
    pack_p.add_argument("repo")
    pack_p.add_argument("--tag", required=True)
    pack_p.add_argument("--out", default="dist-packages")
    pack_p.add_argument("--sign", action="store_true", help="also write the .sig (needs the key of the releases)")
    commands.add_parser("sign").add_argument("package")
    commands.add_parser("verify").add_argument("package")
    args = parser.parse_args(argv)
    if args.command == "pack":
        package = pack(Path(args.repo), args.tag, Path(args.out))
        print(package.name)
        if args.sign:
            print(sign(package).name + "  signed")
        return 0
    if args.command == "sign":
        print(sign(Path(args.package).resolve()).name + "  signed")
        return 0
    try:
        result = package_release.verify_package(Path(args.package).resolve())
    except package_release.PackageError as error:
        print(f"PACKAGE=REFUSED {error}", file=sys.stderr)
        return 1
    print(f"PACKAGE=OK {result.name} {result.version} {result.sha256}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
