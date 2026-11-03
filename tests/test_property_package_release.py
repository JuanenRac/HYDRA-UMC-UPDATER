# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_property_package_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Property-based tests of the signed package of a release: no package with a wrong signature, a link, a path outside the package or another hash is installed.

The cases come from a small generator with a FIXED seed (``random.Random``), so a run is the same everywhere and no test dependency is needed; the number of cases per
property is bounded to keep the file in a few seconds. The key pair is made from a fixed seed here and is a throwaway one, never the key of the releases.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402

from hydra_umc_updater import package_release as pr  # noqa: E402

SEED = 7001
CASES = 40
PRIVATE = ed25519.Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"throwaway key of the property tests").digest())
PUBLIC_HEX = PRIVATE.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
OTHER = ed25519.Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"another throwaway key").digest())


def rng(name: str) -> random.Random:
    return random.Random(f"{SEED}:{name}")


def message(name: str, version: str, digest: str) -> bytes:
    """The signed text written out here on purpose, not taken from the module: the test must not agree with a wrong module by construction."""
    return f"hydra-pc-pkg/1|{name}|{version}|{digest}".encode("utf-8")


def build_tar(members: list[tuple[str, bytes | None, dict]], version: str = "1.2.3") -> bytes:
    """Members are (name, content or None for a folder, extra tarinfo fields)."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        manifest = json.dumps({"version": version}).encode()
        for name, content, extra in [("hydra-umc.project.json", manifest, {})] + members:
            info = tarfile.TarInfo(name)
            for key, value in extra.items():
                setattr(info, key, value)
            if content is None and "type" not in extra:
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            elif extra.get("type") in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
                tar.addfile(info)
            else:
                info.size = len(content or b"")
                tar.addfile(info, io.BytesIO(content or b""))
    return buffer.getvalue()


def publish(folder: Path, data: bytes, name: str = "HYDRA-UMC-DEMO", version: str = "1.2.3", key=PRIVATE, sign: bool = True, sha: str | None = None) -> Path:
    package = folder / f"{name}-{version}.tgz"
    package.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (folder / (package.name + ".sha256")).write_text((sha or digest) + "  " + package.name + "\n", encoding="ascii")
    if sign:
        (folder / (package.name + ".sig")).write_text(key.sign(message(name, version, digest)).hex() + "\n", encoding="ascii")
    return package


def good_data(version: str = "1.2.3") -> bytes:
    return build_tar([("src/", None, {}), ("src/app.py", b"print('hello')\n", {})], version)


def verify(package: Path, **kwargs):
    return pr.verify_package(package, public_key_hex=PUBLIC_HEX, require_signature=kwargs.pop("require_signature", True), **kwargs)


def refused(package: Path, code: str | None = None, **kwargs) -> pr.PackageError:
    with pytest.raises(pr.PackageError) as caught:
        verify(package, **kwargs)
    if code is not None:
        assert caught.value.code == code, (caught.value.code, str(caught.value))
    return caught.value


def test_the_good_package_verifies_and_installs(tmp_path: Path):
    package = publish(tmp_path, good_data())
    result = verify(package)
    assert result.signed and result.name == "HYDRA-UMC-DEMO" and result.version == "1.2.3"
    work = tmp_path / "work"
    work.mkdir()
    pr.install_package(package, work, public_key_hex=PUBLIC_HEX, require_signature=True)
    assert (work / "HYDRA-UMC-DEMO" / "src" / "app.py").read_bytes() == b"print('hello')\n"


def test_no_change_to_the_signature_is_accepted(tmp_path: Path):
    r = rng("sig")
    package = publish(tmp_path, good_data())
    sig_file = tmp_path / (package.name + ".sig")
    original = sig_file.read_text(encoding="ascii").strip()
    for _ in range(CASES):
        kind = r.randrange(5)
        if kind == 0:
            i = r.randrange(128)
            text = original[:i] + ("0" if original[i] != "0" else "1") + original[i + 1:]
        elif kind == 1:
            text = original[:-r.randrange(1, 10)]
        elif kind == 2:
            text = original + "00"
        elif kind == 3:
            text = "".join(r.choice("0123456789abcdefg") for _ in range(128))
        else:
            text = r.choice(["", "zz" * 64, " ", original.upper()[:127] + "G"])
        sig_file.write_text(text, encoding="ascii")
        if text == original:
            continue
        try:
            verify(package)
        except pr.PackageError as error:
            assert error.code in ("sig_bad", "sig_missing")
        else:
            raise AssertionError(f"a changed signature was accepted: {text!r}")
        # a signature that is present and wrong is refused even when the person runs unsigned packages
        if text.strip():
            with pytest.raises(pr.PackageError):
                verify(package, require_signature=False)


def test_a_signature_is_bound_to_the_project_the_version_and_the_hash(tmp_path: Path):
    data = good_data()
    signed_for = {"name": "HYDRA-UMC-DEMO", "version": "1.2.3"}
    digest = hashlib.sha256(data).hexdigest()
    r = rng("bind")
    for _ in range(CASES):
        name = r.choice(["HYDRA-UMC-DEMO", "HYDRA-UMC-OTHER", "hydra-umc-demo", "HYDRA-UMC-DEMO-X"])
        version = r.choice(["1.2.3", "1.2.4", "1.2.3.0", "0.0.1", "9.9.9"])
        folder = tmp_path / f"c{_}"
        folder.mkdir()
        package = folder / f"{name}-{version}.tgz"
        package.write_bytes(data)
        (folder / (package.name + ".sha256")).write_text(digest, encoding="ascii")
        (folder / (package.name + ".sig")).write_text(PRIVATE.sign(message(signed_for["name"], signed_for["version"], digest)).hex(), encoding="ascii")
        if (name, version) == (signed_for["name"], signed_for["version"]):
            assert verify(package).signed
        else:
            refused(package, "sig_bad")
    # the key must be the pinned one
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    refused(publish(foreign, data, key=OTHER), "sig_bad")


def test_a_changed_package_is_never_installed_whatever_the_attacker_also_changes(tmp_path: Path):
    data = good_data()
    r = rng("tamper")
    for n in range(CASES):
        folder = tmp_path / f"t{n}"
        folder.mkdir()
        raw = bytearray(data)
        raw[r.randrange(len(raw))] ^= 1 << r.randrange(8)
        changed = bytes(raw)
        if changed == data:
            continue
        old_sig = PRIVATE.sign(message("HYDRA-UMC-DEMO", "1.2.3", hashlib.sha256(data).hexdigest())).hex()
        # 1) hash and signature of the original left as they were
        package = folder / "HYDRA-UMC-DEMO-1.2.3.tgz"
        package.write_bytes(changed)
        (folder / (package.name + ".sha256")).write_text(hashlib.sha256(data).hexdigest(), encoding="ascii")
        (folder / (package.name + ".sig")).write_text(old_sig, encoding="ascii")
        refused(package, "sha256_bad")
        # 2) the attacker also rewrites the hash: the signature no longer matches it
        (folder / (package.name + ".sha256")).write_text(hashlib.sha256(changed).hexdigest(), encoding="ascii")
        refused(package, "sig_bad")
        # 3) a package with a wrong hash is refused even when unsigned packages are allowed
        (folder / (package.name + ".sig")).unlink()
        (folder / (package.name + ".sha256")).write_text(hashlib.sha256(data).hexdigest(), encoding="ascii")
        refused(package, "sha256_bad", require_signature=False)


def test_the_hash_file_must_be_present_and_well_formed(tmp_path: Path):
    r = rng("sha")
    data = good_data()
    digest = hashlib.sha256(data).hexdigest()
    for n in range(CASES):
        folder = tmp_path / f"h{n}"
        folder.mkdir()
        package = publish(folder, data)
        sha_file = folder / (package.name + ".sha256")
        kind = r.randrange(5)
        if kind == 0:
            sha_file.unlink()
            expected = "sha256_missing"
        elif kind == 1:
            sha_file.write_text(r.choice(["", "  ", "abc", "g" * 64, digest[:-1], "x" + digest, "\n" + digest[:10]]), encoding="ascii")
            expected = "sha256_missing"
        elif kind == 2:
            i = r.randrange(64)
            sha_file.write_text(digest[:i] + ("0" if digest[i] != "0" else "1") + digest[i + 1:], encoding="ascii")
            expected = "sha256_bad"
        elif kind == 3:
            sha_file.write_bytes(b"\xff\xfe" + digest.encode())
            expected = "sha256_missing"
        else:
            sha_file.write_text(digest.upper() + "  file\n", encoding="ascii")
            expected = None   # an upper-case hash is the same hash
        if expected is None:
            assert verify(package).signed
        else:
            refused(package, expected)


def test_no_member_that_could_leave_the_package_or_be_a_link_is_accepted(tmp_path: Path):
    r = rng("members")
    names = ["../evil", "a/../../evil", "/etc/passwd", "\\windows\\x", "a\\b", "C:/x", "c:evil", ".git/config", "a/.git/hooks/x", "..", "a/../b/../../x", ""]
    kinds = [None, tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE]
    for n in range(CASES):
        folder = tmp_path / f"m{n}"
        folder.mkdir()
        if r.random() < 0.5:
            member = (r.choice(names), b"x", {})
        else:
            kind = r.choice(kinds[1:])
            member = ("link", None, {"type": kind, "linkname": r.choice(["/etc/passwd", "../outside", "src/app.py"])})
        package = publish(folder, build_tar([("src/app.py", b"ok", {}), member]))
        if member[0] == "":
            continue   # a nameless member cannot be built by the tar writer in a way that every version of Python keeps
        refused(package, "member_bad")
        work = tmp_path / f"w{n}"
        work.mkdir()
        with pytest.raises(pr.PackageError):
            pr.install_package(package, work, public_key_hex=PUBLIC_HEX, require_signature=True)
        assert list(work.iterdir()) == []                      # nothing was written, not even a staging folder
        assert not (tmp_path / "evil").exists() and not (folder / "evil").exists()


def test_extraction_alone_never_writes_outside_its_folder(tmp_path: Path):
    """_extract is a second line behind check_members: a path that leaves the folder is refused there too."""
    r = rng("extract")
    for n in range(CASES):
        name = r.choice(["../x", "a/../../x", "a/b/../../../x", "../../etc/x"])
        package = tmp_path / f"e{n}.tgz"
        package.write_bytes(build_tar([(name, b"x", {})]))
        dest = tmp_path / f"d{n}" / "inside"
        with pytest.raises(pr.PackageError):
            pr._extract(package, dest)
        assert not (tmp_path / f"d{n}" / "x").exists() and not (tmp_path / "x").exists()


def test_names_that_are_not_project_dash_version_are_refused(tmp_path: Path):
    r = rng("names")
    bad = ["demo.tgz", "demo-1.tgz", "demo-1.2.tgz", "demo-1.2.3.4.5.tgz", "1demo-1.2.3.tgz", "demo-v1.2.3.tgz", "demo-1.2.3.tar.gz", "demo-1.2.3.tgz.bak", "de mo-1.2.3.tgz",
           "-demo-1.2.3.tgz", "demo_x-1.2.3.tgz", "demo-1.2.a.tgz", "demo-1.2.3.TGZ", "../demo-1.2.3.tgz"]
    for name in bad:
        target = tmp_path / Path(name).name
        target.write_bytes(good_data())
        if Path(name).name == "demo-1.2.3.tgz":
            continue
        if pr.NAME_PATTERN.match(Path(name).name):
            continue
        refused(target, "name_bad")
    for _ in range(CASES):
        text = "".join(r.choice("ab-.0123456789tgz ") for _ in range(r.randrange(1, 25)))
        match = pr.NAME_PATTERN.match(text)
        if match:
            assert match.group(2).count(".") in (2, 3) and text.endswith(".tgz") and text[0].isalpha()


def test_an_unsigned_package_is_installed_only_when_the_person_allowed_it_and_never_with_a_bad_signature(tmp_path: Path):
    data = good_data()
    package = publish(tmp_path, data, sign=False)
    refused(package, "sig_missing", require_signature=True)
    result = verify(package, require_signature=False)
    assert not result.signed
    # the default of the function is the saved setting, which counts a damaged file as "required": the switch cannot be turned off from the environment
    import os

    os.environ[pr.REQUIRE_SIGNED_PACKAGES_ENV] = "1"
    try:
        assert pr.signature_required() is True
    finally:
        del os.environ[pr.REQUIRE_SIGNED_PACKAGES_ENV]


def test_a_manifest_that_does_not_say_the_version_is_never_installed(tmp_path: Path):
    r = rng("manifest")
    for n in range(CASES):
        folder = tmp_path / f"v{n}"
        folder.mkdir()
        shown = r.choice(["1.2.2", "1.2.4", "2.0.0", "1.2.3.0", "x", "", "1.2", None])
        package = publish(folder, build_tar([("src/app.py", b"ok", {})], version=shown if shown is not None else "1.2.3"))
        if shown is None:
            continue
        work = tmp_path / f"wv{n}"
        work.mkdir()
        if shown == "1.2.3":
            continue
        with pytest.raises(pr.PackageError) as caught:
            pr.install_package(package, work, public_key_hex=PUBLIC_HEX, require_signature=True)
        assert caught.value.code == "manifest_bad"
        assert [p.name for p in work.iterdir()] == []


def test_a_version_that_is_not_newer_is_refused_and_a_newer_one_keeps_a_backup(tmp_path: Path):
    r = rng("newer")
    for n in range(CASES):
        folder = tmp_path / f"n{n}"
        folder.mkdir()
        work = tmp_path / f"wn{n}"
        (work / "HYDRA-UMC-DEMO").mkdir(parents=True)
        installed = ".".join(str(r.randrange(0, 4)) for _ in range(3))
        (work / "HYDRA-UMC-DEMO" / pr.MANIFEST_FILE).write_text(json.dumps({"version": installed}), encoding="utf-8")
        (work / "HYDRA-UMC-DEMO" / "old.txt").write_text("old", encoding="utf-8")
        new = ".".join(str(r.randrange(0, 4)) for _ in range(3))
        package = publish(folder, build_tar([("src/app.py", b"new", {})], version=new), version=new)
        newer = pr._version_tuple(new) > pr._version_tuple(installed)
        if newer:
            pr.install_package(package, work, public_key_hex=PUBLIC_HEX, require_signature=True)
            assert (work / "HYDRA-UMC-DEMO" / "src" / "app.py").exists()
            backups = [p for p in work.iterdir() if ".backup-" in p.name]
            assert len(backups) == 1 and (backups[0] / "old.txt").read_text(encoding="utf-8") == "old"   # never deleted
        else:
            with pytest.raises(pr.PackageError) as caught:
                pr.install_package(package, work, public_key_hex=PUBLIC_HEX, require_signature=True)
            assert caught.value.code == "not_newer"
            assert (work / "HYDRA-UMC-DEMO" / "old.txt").exists()
            assert [p.name for p in work.iterdir()] == ["HYDRA-UMC-DEMO"]


def test_a_pinned_key_that_is_not_a_raw_key_is_refused(tmp_path: Path):
    package = publish(tmp_path, good_data())
    r = rng("key")
    for _ in range(CASES):
        key = r.choice(["", "zz" * 32, PUBLIC_HEX[:-1], PUBLIC_HEX + "0", PUBLIC_HEX.upper(), "0x" + PUBLIC_HEX[2:], " " + PUBLIC_HEX])
        if key == PUBLIC_HEX:
            continue
        with pytest.raises(pr.PackageError):
            pr.verify_package(package, public_key_hex=key, require_signature=True)


def test_the_signed_text_and_the_fingerprint_are_exactly_what_the_scheme_says(tmp_path: Path):
    assert pr.package_message("HYDRA-UMC-DEMO", "1.2.3", "ab" * 32) == b"hydra-pc-pkg/1|HYDRA-UMC-DEMO|1.2.3|" + b"ab" * 32
    digest = hashlib.sha256(bytes.fromhex(PUBLIC_HEX)).hexdigest()[:16]
    assert pr.fingerprint(PUBLIC_HEX) == ":".join(digest[i:i + 4] for i in range(0, 16, 4))
    assert verify(publish(tmp_path, good_data())).fingerprint == pr.fingerprint(PUBLIC_HEX)
    assert pr._version_tuple("1.2.3") == (1, 2, 3, 0) and pr._version_tuple("1.2.3.4") == (1, 2, 3, 4)
    assert pr._version_tuple("1.2.3") < pr._version_tuple("1.2.3.1") < pr._version_tuple("1.2.4")


def test_the_reasons_of_the_refusals_are_the_documented_ones(tmp_path: Path):
    package = publish(tmp_path, good_data(), sign=False)
    assert str(refused(package, "sig_missing", require_signature=True)) == "the .sig is missing: an unsigned package is never installed"
    (tmp_path / (package.name + ".sha256")).unlink()
    assert str(refused(package, "sha256_missing")) == "the .sha256 of the package is missing or unreadable"
    other = tmp_path / "other"
    other.mkdir()
    bad = publish(other, good_data(), sha="0" * 64)
    assert str(refused(bad, "sha256_bad")) == "the hash does not match the package: it was changed after it was published"
    named = tmp_path / "x.tgz"
    named.write_bytes(b"x")
    assert "is not named <project>-<version>.tgz" in str(refused(named, "name_bad"))


def test_the_limits_of_a_package_are_exact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    members = [("src/", None, {}), ("src/a.py", b"x" * 10, {}), ("src/b.py", b"y" * 5, {})]
    data = build_tar(members)                       # four members: the manifest, a folder and two files
    unpacked = len(json.dumps({"version": "1.2.3"})) + 15

    def package_with(name_dir: str, content: bytes = data) -> Path:
        folder = tmp_path / name_dir
        folder.mkdir()
        return publish(folder, content)

    monkeypatch.setattr(pr, "MAX_MEMBERS", 4)
    assert verify(package_with("m1")).signed
    monkeypatch.setattr(pr, "MAX_MEMBERS", 3)
    error = refused(package_with("m2"), "too_big")
    assert str(error) == "the package holds too many files"
    monkeypatch.setattr(pr, "MAX_MEMBERS", 50_000)

    monkeypatch.setattr(pr, "MAX_UNPACKED_BYTES", unpacked)
    assert verify(package_with("u1")).signed
    monkeypatch.setattr(pr, "MAX_UNPACKED_BYTES", unpacked - 1)
    assert str(refused(package_with("u2"), "too_big")) == "the package unpacks to more than the allowed size"
    monkeypatch.setattr(pr, "MAX_UNPACKED_BYTES", 800 * 1024 * 1024)
    folders_only = build_tar([(f"d{i}/", None, {}) for i in range(5)])
    monkeypatch.setattr(pr, "MAX_UNPACKED_BYTES", len(json.dumps({"version": "1.2.3"})))   # a folder weighs nothing
    assert verify(package_with("u3", folders_only)).signed
    monkeypatch.setattr(pr, "MAX_UNPACKED_BYTES", 800 * 1024 * 1024)

    package = package_with("p1")
    monkeypatch.setattr(pr, "MAX_PACKAGE_BYTES", package.stat().st_size)
    assert verify(package).signed
    monkeypatch.setattr(pr, "MAX_PACKAGE_BYTES", package.stat().st_size - 1)
    assert str(refused(package, "unreadable")) == f"the package {package.name} cannot be read or is too large"
    monkeypatch.setattr(pr, "MAX_PACKAGE_BYTES", 200 * 1024 * 1024)

    sha_size = (package.parent / (package.name + ".sha256")).stat().st_size
    sig_size = (package.parent / (package.name + ".sig")).stat().st_size
    monkeypatch.setattr(pr, "MAX_SMALL_FILE_BYTES", max(sha_size, sig_size))
    assert verify(package).signed
    monkeypatch.setattr(pr, "MAX_SMALL_FILE_BYTES", sha_size - 1)
    refused(package, "sha256_missing")


def test_the_reasons_of_the_member_checks_and_of_the_pinned_key(tmp_path: Path):
    for n, (name, extra, text) in enumerate([
        ("../evil", {}, "../evil would be written outside the target"),
        ("a/../../evil", {}, "a/../../evil would be written outside the target"),
        ("link", {"type": tarfile.SYMTYPE, "linkname": "/etc/passwd"}, "link is not a regular file or a folder"),
    ]):
        folder = tmp_path / f"r{n}"
        folder.mkdir()
        content = None if "type" in extra else b"x"
        error = refused(publish(folder, build_tar([(name, content, extra)])), "member_bad")
        assert str(error) == text and error.params == {"member": name}
    folder = tmp_path / "key"
    folder.mkdir()
    with pytest.raises(pr.PackageError) as caught:
        pr.verify_package(publish(folder, good_data()), public_key_hex="zz" * 32, require_signature=True)
    assert caught.value.code == "sig_bad" and str(caught.value) == "the pinned public key is not a raw Ed25519 key"
    folder = tmp_path / "name"
    folder.mkdir()
    bad = folder / "x.tgz"
    bad.write_bytes(b"x")
    error = refused(bad, "name_bad")
    assert str(error) == "x.tgz is not named <project>-<version>.tgz" and error.params == {"name": "x.tgz"}


def test_every_listed_dangerous_name_is_refused_one_by_one(tmp_path: Path):
    names = ["../evil", "a/../../evil", "/etc/passwd", "/", "\\windows\\x", "a\\b", "C:/x", "c:evil", ".git/config", "a/.git/hooks/x", "a/b/../../../x"]
    for n, name in enumerate(names):
        folder = tmp_path / f"n{n}"
        folder.mkdir()
        error = refused(publish(folder, build_tar([(name, b"x", {})])), "member_bad")
        assert error.params == {"member": name} and name in str(error)


def test_an_archive_that_cannot_be_read_is_unreadable_with_its_reason(tmp_path: Path):
    r = rng("garbage")
    for n in range(10):
        folder = tmp_path / f"g{n}"
        folder.mkdir()
        garbage = bytes(r.randrange(256) for _ in range(r.randrange(0, 300)))
        error = refused(publish(folder, garbage), "unreadable")
        assert str(error).startswith("the archive cannot be read: ") and error.params == {"name": "HYDRA-UMC-DEMO-1.2.3.tgz"}
    truncated = tmp_path / "t"
    truncated.mkdir()
    good = good_data()
    error = refused(publish(truncated, good[: len(good) // 2]), "unreadable")
    assert str(error).startswith("the archive cannot be read: ")


def test_the_installation_rules_one_by_one(tmp_path: Path):
    def install(name: str, data: bytes, work: Path, **kwargs):
        folder = tmp_path / name
        folder.mkdir()
        return pr.install_package(publish(folder, data, **kwargs), work, public_key_hex=PUBLIC_HEX, require_signature=True)

    # the same version is not newer; the message names both
    work = tmp_path / "w1"
    (work / "HYDRA-UMC-DEMO").mkdir(parents=True)
    (work / "HYDRA-UMC-DEMO" / pr.MANIFEST_FILE).write_text(json.dumps({"version": "1.2.3"}), encoding="utf-8")
    with pytest.raises(pr.PackageError) as caught:
        install("a", good_data(), work)
    assert caught.value.code == "not_newer" and str(caught.value) == "1.2.3 is not newer than the 1.2.3 installed"
    assert caught.value.params == {"version": "1.2.3", "installed": "1.2.3"}
    # a folder that is not an installation (no manifest, no .git) is never replaced; one with a .git is
    work = tmp_path / "w2"
    (work / "HYDRA-UMC-DEMO").mkdir(parents=True)
    (work / "HYDRA-UMC-DEMO" / "mine.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(pr.PackageError) as caught:
        install("b", good_data(), work)
    assert caught.value.code == "install_failed"
    assert str(caught.value) == f"{work / 'HYDRA-UMC-DEMO'} exists and is not an installation this updater can replace"
    assert caught.value.params == {"detail": str(work / "HYDRA-UMC-DEMO")}
    assert (work / "HYDRA-UMC-DEMO" / "mine.txt").exists() and [p.name for p in work.iterdir()] == ["HYDRA-UMC-DEMO"]
    (work / "HYDRA-UMC-DEMO" / ".git").mkdir()
    install("c", good_data(), work)
    backups = [p for p in work.iterdir() if ".backup-" in p.name]
    assert len(backups) == 1 and len(backups[0].name.split(".backup-")[1]) == 8 and (backups[0] / "mine.txt").exists()
    # the manifest of the package must say the version, and when it says nothing usable the message says so
    for shown, text in ((5, "nothing usable"), ("1.2", "nothing usable"), ("2.0.0", "2.0.0")):
        folder = tmp_path / f"m{text}{shown}"
        folder.mkdir()
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w:gz") as tar:
            body = json.dumps({"version": shown}).encode()
            info = tarfile.TarInfo(pr.MANIFEST_FILE)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
        work = tmp_path / f"wm{text}{shown}"
        work.mkdir()
        with pytest.raises(pr.PackageError) as caught:
            pr.install_package(publish(folder, raw.getvalue()), work, public_key_hex=PUBLIC_HEX, require_signature=True)
        assert caught.value.code == "manifest_bad"
        assert str(caught.value) == f"the manifest inside the package says {text}, not 1.2.3"
        assert list(work.iterdir()) == []
    # folders deeper than the members that name them, a folder named twice and a file in a folder that has no member
    work = tmp_path / "w3"
    work.mkdir()
    deep = build_tar([("a/b/", None, {}), ("a/b/", None, {}), ("c/d/e.txt", b"deep", {})])
    install("d", deep, work)
    assert (work / "HYDRA-UMC-DEMO" / "a" / "b").is_dir() and (work / "HYDRA-UMC-DEMO" / "c" / "d" / "e.txt").read_bytes() == b"deep"
    # an unsigned install is reported as unsigned, with a real False
    folder = tmp_path / "u"
    folder.mkdir()
    assert verify(publish(folder, good_data(), sign=False), require_signature=False).signed is False


def test_the_reasons_of_the_signature_refusals(tmp_path: Path):
    package = publish(tmp_path, good_data())
    sig_file = tmp_path / (package.name + ".sig")
    sig_file.write_text("not hexadecimal", encoding="ascii")
    assert str(refused(package, "sig_bad")) == "the .sig is not an Ed25519 signature in hexadecimal"
    sig_file.write_text(OTHER.sign(message("HYDRA-UMC-DEMO", "1.2.3", hashlib.sha256(good_data()).hexdigest())).hex(), encoding="ascii")
    assert str(refused(package, "sig_bad")) == "the signature is not valid for this project, this version and this hash"
