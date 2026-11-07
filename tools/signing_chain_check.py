#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC-UPDATER - tools/signing_chain_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signing chain from end to end with throw-away keys: what the image builder signs, the updater verifies.

Everything is made in a temporary folder with keys generated for this run and removed at the end; no real key is read, written or needed. Four chains:

1. image release: the image builder writes and signs `release.json`; the updater verifies it with a file of trusted public keys (good, tampered image,
   tampered manifest, wrong key, revoked key, missing signature);
2. golden image: the builder registers and signs it; its own verification accepts it and refuses a changed image, a downgrade and an older minimum;
3. package: a signed `.hef` package is verified and installed by the updater; a changed package, the signature of another project, an older version and a
   missing signature are refused and nothing is installed;
4. update manifest: signed with the canonical-JSON rule of the contract and checked with the validator of the SDK; a simulated bootloader refuses a manifest
   that needs a newer bootloader, one for another target and one whose signature does not verify.

The bootloader of chain 4 is a model written here (a version, a target and the key it trusts): the comparison on a real board is pending hardware.
evidence=simulator. Usage: signing_chain_check.py --rebuilder-src DIR --sdk-src DIR  (the `src` folder of the image builder and the Python client of the SDK).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RESULTS: list[tuple[bool, str]] = []


def check(condition: bool, message: str) -> None:
    RESULTS.append((bool(condition), message))
    print(("PASS  " if condition else "FAIL  ") + message)


def refuses(call, code: str | None, message: str) -> None:
    """The call raises; when `code` is given, the error carries it."""
    try:
        call()
    except Exception as error:  # noqa: BLE001 - the kind of error is checked below
        got = getattr(error, "code", None)
        check(code is None or got == code, f"{message} (refused as {got or type(error).__name__})")
        return
    check(False, f"{message} (was accepted)")


def canonical(document: dict) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuilder-src", required=True)
    parser.add_argument("--sdk-src", required=True)
    args = parser.parse_args()
    sys.path[:0] = [str(HERE / "src"), args.rebuilder_src, args.sdk_src]

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    from hydra_umc_os_rebuilder import golden_image, profile_signing, release_channel
    from hydra_umc_sdk import validation
    from hydra_umc_updater import image_release, package_release

    def raw_public(private) -> str:
        return private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    with tempfile.TemporaryDirectory(prefix="hydra-signing-chain-") as temp:
        tmp = Path(temp)
        keys = tmp / "keys"
        keys.mkdir()
        private_file, public_file = keys / "release.key", keys / "release.pub"
        public = profile_signing.generate_keypair(private_file, public_file)
        other_private = ed25519.Ed25519PrivateKey.generate()
        other_public = raw_public(other_private)
        check(public != other_public, "two throw-away keys were made for this run")
        config = {"release_channel": {"tag_prefix": "image-v"}}
        commit = "b" * 40

        # 1. image release
        work = tmp / "release"
        work.mkdir()
        image = work / "hydra.img"
        image.write_bytes(os.urandom(256 * 1024))
        manifest = release_channel.make_manifest(image, "0.4.0", commit, work / "release.json", config)
        release_channel.sign_release(manifest, str(private_file))
        trusted = tmp / "trusted.txt"
        trusted.write_text(public + " test key\n", encoding="utf-8")
        trusted_keys = image_release.load_trusted_keys(trusted)
        result = image_release.verify_release(manifest, image, trusted_keys)
        check(result.version == "0.4.0" and "signature" in result.checked and "sha256" in result.checked, "the updater accepts the release the builder signed")
        flipped = tmp / "flipped.img"
        data = bytearray(image.read_bytes())
        data[1000] ^= 0x01
        flipped.write_bytes(bytes(data))
        refuses(lambda: image_release.verify_release(manifest, flipped, trusted_keys), "image_mismatch", "a changed image is refused")
        changed = work / "changed" / "release.json"
        changed.parent.mkdir()
        changed.write_text(manifest.read_text(encoding="utf-8").replace("0.4.0", "9.9.9"), encoding="utf-8")
        (changed.parent / "release.json.sig").write_bytes((work / "release.json.sig").read_bytes())
        refuses(lambda: image_release.verify_release(changed, image, trusted_keys), "signature_bad", "a changed manifest is refused")
        wrong = tmp / "wrong.txt"
        wrong.write_text(other_public + "\n", encoding="utf-8")
        refuses(lambda: image_release.verify_release(manifest, image, image_release.load_trusted_keys(wrong)), "signature_bad", "a release signed by another key is refused")
        revoked = tmp / "revoked.txt"
        revoked.write_text(other_public + "\nrevoke " + public + "\n", encoding="utf-8")
        refuses(lambda: image_release.verify_release(manifest, image, image_release.load_trusted_keys(revoked)), "key_revoked", "a release signed by a revoked key is refused")
        unsigned = work / "unsigned"
        unsigned.mkdir()
        (unsigned / "release.json").write_bytes(manifest.read_bytes())
        refuses(lambda: image_release.verify_release(unsigned / "release.json", image, trusted_keys), "no_signature", "a release without a signature is refused")
        own = release_channel.verify_release(manifest, image, {"release_channel": {"tag_prefix": "image-v", "require_signed_manifest": True, "require_signed_tag": False, "trusted_key": public}})
        check(own["version"] == "0.4.0" and "signature" in own["checked"], "the builder's own verification agrees with the updater")

        # 2. golden image
        store = tmp / "golden"
        record = golden_image.register(image, store, "0.4.0", commit, str(private_file))
        check(golden_image.verify(store, public)["version"] == "0.4.0", "the golden image the builder registered verifies")
        refuses(lambda: golden_image.register(image, store, "0.3.0", commit, str(private_file), replace=True), None, "a golden image that goes back is refused")
        refuses(lambda: golden_image.verify(store, other_public), None, "the golden record does not verify with another key")
        refuses(lambda: golden_image.verify(store, public, minimum_version="0.5.0"), None, "a golden image older than the minimum is refused")
        (store / image.name).write_bytes(bytes(data))
        refuses(lambda: golden_image.verify(store, public), None, "a golden image changed in the store is refused")
        check(record.is_file(), "the golden record exists")

        # 3. package of a model
        def package(project: str, version: str, files: dict[str, bytes], folder: Path, signer=None, sign_as: tuple[str, str] | None = None) -> Path:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{project}-{version}.tgz"
            with tarfile.open(path, "w:gz") as archive:
                members = {"hydra-umc.project.json": json.dumps({"name": project, "version": version}).encode(), **files}
                for name, content in members.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            digest = package_release.file_sha256(path)
            (folder / (path.name + ".sha256")).write_text(f"{digest}  {path.name}\n", encoding="utf-8")
            if signer is not None:
                name, number = sign_as or (project, version)
                (folder / (path.name + ".sig")).write_text(signer.sign(package_release.package_message(name, number, digest)).hex() + "\n", encoding="ascii")
            return path

        signer = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_file.read_text().strip()))
        model = os.urandom(4096)
        workspace = tmp / "workspace"
        workspace.mkdir()
        good = package("HYDRA-UMC-DETECTION-HEF", "1.2.0", {"models/person.hef": model}, tmp / "pk1", signer)
        installed = package_release.install_package(good, workspace, public_key_hex=public, require_signature=True)
        check(installed.signed and (workspace / "HYDRA-UMC-DETECTION-HEF" / "models" / "person.hef").read_bytes() == model, "a signed model package installs and the .hef arrives intact")
        older = package("HYDRA-UMC-DETECTION-HEF", "1.1.0", {"models/person.hef": b"old"}, tmp / "pk2", signer)
        refuses(lambda: package_release.install_package(older, workspace, public_key_hex=public, require_signature=True), "not_newer", "an older signed version is not installed over the newer one")
        tampered = package("HYDRA-UMC-DETECTION-HEF", "1.3.0", {"models/person.hef": model}, tmp / "pk3", signer)
        with tampered.open("r+b") as handle:
            handle.seek(40)
            handle.write(b"\x00\x00\x00\x00")
        refuses(lambda: package_release.verify_package(tampered, public_key_hex=public, require_signature=True), "sha256_bad", "a package changed after publication is refused")
        foreign = package("HYDRA-UMC-DETECTION-HEF", "1.4.0", {"models/person.hef": model}, tmp / "pk4", other_private)
        refuses(lambda: package_release.verify_package(foreign, public_key_hex=public, require_signature=True), "sig_bad", "a package signed by another key is refused")
        replay = package("HYDRA-UMC-DETECTION-HEF", "1.5.0", {"models/person.hef": model}, tmp / "pk5", signer, sign_as=("HYDRA-UMC-SERVER", "1.5.0"))
        refuses(lambda: package_release.verify_package(replay, public_key_hex=public, require_signature=True), "sig_bad", "the signature of another project cannot be reused")
        nosig = package("HYDRA-UMC-DETECTION-HEF", "1.6.0", {"models/person.hef": model}, tmp / "pk6")
        refuses(lambda: package_release.install_package(nosig, workspace, public_key_hex=public, require_signature=True), "sig_missing", "an unsigned package is not installed")
        check(sorted(p.name for p in workspace.iterdir() if p.name.startswith("HYDRA")) == ["HYDRA-UMC-DETECTION-HEF"] and not any(".package-" in p.name for p in workspace.iterdir()), "after the refusals only the good install is in the workspace and no staging folder is left")

        # 4. update manifest and a simulated bootloader
        key_id = hashlib.sha512(bytes.fromhex(public)).digest()[:8].hex()

        def update(**over) -> dict:
            body = {
                "schema_version": "1.0", "project": "HYDRA-UMC", "version": "0.4.0", "artifact_url": "https://example.invalid/firmware.bin",
                "sha256": hashlib.sha256(b"firmware").hexdigest(), "signature_alg": "ed25519", "key_id": key_id, "min_bootloader": "0.2.0", "target": "g474",
            }
            body.update(over)
            return {**body, "signature": signer.sign(canonical(body)).hex()}

        class SimulatedBootloader:
            """The decision of a bootloader as a model: the key it trusts, its own version and the controller it runs on."""

            def __init__(self, trusted_public: str, version: tuple[int, int, int], target: str) -> None:
                self.public, self.version, self.target = trusted_public, version, target

            def accepts(self, manifest: dict) -> str:
                validation.validate("UpdateManifest", manifest)
                body = {k: v for k, v in manifest.items() if k != "signature"}
                try:
                    ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public)).verify(bytes.fromhex(manifest["signature"]), canonical(body))
                except Exception:  # noqa: BLE001
                    return "bad_signature"
                if manifest.get("target") not in (None, self.target):
                    return "wrong_target"
                if tuple(int(p) for p in manifest.get("min_bootloader", "0.0.0").split(".")) > self.version:
                    return "bootloader_too_old"
                return "accepted"

        board = SimulatedBootloader(public, (0, 2, 1), "g474")
        check(board.accepts(update()) == "accepted", "a signed manifest for this board and this bootloader is accepted")
        check(board.accepts(update(min_bootloader="0.3.0")) == "bootloader_too_old", "a manifest that needs a newer bootloader is refused")
        check(board.accepts(update(target="h745-cm7")) == "wrong_target", "a manifest for another controller is refused")
        forged = update()
        forged["version"] = "9.9.9"
        check(board.accepts(forged) == "bad_signature", "a manifest edited after signing is refused")
        check(SimulatedBootloader(other_public, (0, 2, 1), "g474").accepts(update()) == "bad_signature", "a manifest signed by a key the board does not trust is refused")

    failed = [m for ok, m in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} checks passed; evidence=simulator (throw-away keys, no board, no real key)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
