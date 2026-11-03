# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_package_release.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Signed packages of a release. The keys are made by the test: the key of the releases is never needed. No network."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402

from hydra_umc_updater import main as main_module  # noqa: E402
from hydra_umc_updater import package_release, release_channel, settings  # noqa: E402
from hydra_umc_updater.package_release import PackageError, fetch_release_package, install_package, verify_package  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import package_pc_release  # noqa: E402

KEY = ed25519.Ed25519PrivateKey.generate()
OTHER = ed25519.Ed25519PrivateKey.generate()


def public_hex(key: ed25519.Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


PUBLIC = public_hex(KEY)


def manifest(version: str) -> bytes:
    return json.dumps({"name": "DEMO", "version": version}).encode()


def make_package(folder: Path, name: str = "DEMO", version: str = "1.2.0", *, members: dict[str, bytes] | None = None,
                 key: ed25519.Ed25519PrivateKey | None = KEY, sign_as: tuple[str, str] | None = None, extra=None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    package = folder / f"{name}-{version}.tgz"
    files = members if members is not None else {"hydra-umc.project.json": manifest(version), "src/app.py": b"print(1)\n"}
    with tarfile.open(package, "w:gz") as tar:
        for path, data in files.items():
            info = tarfile.TarInfo(path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if extra:
            extra(tar)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_name(package.name + ".sha256").write_text(f"{digest}  {package.name}\n", encoding="ascii")
    if key is not None:
        signed_name, signed_version = sign_as or (name, version)
        message = package_release.package_message(signed_name, signed_version, digest)
        package.with_name(package.name + ".sig").write_text(key.sign(message).hex() + "\n", encoding="ascii")
    return package


def verify(package: Path, **kwargs):
    return verify_package(package, public_key_hex=PUBLIC, **kwargs)


def refused(package: Path, code: str, **kwargs) -> None:
    with pytest.raises(PackageError) as caught:
        verify(package, **kwargs)
    assert caught.value.code == code


def test_a_signed_package_holds(tmp_path: Path) -> None:
    result = verify(make_package(tmp_path))
    assert (result.name, result.version, result.signed) == ("DEMO", "1.2.0", True)
    assert len(result.sha256) == 64 and result.fingerprint.count(":") == 3


def test_the_signature_is_required_by_default(tmp_path: Path) -> None:
    refused(make_package(tmp_path, key=None), "sig_missing")


def test_the_requirement_can_be_switched_off_in_the_settings_but_a_wrong_signature_is_still_refused(tmp_path: Path) -> None:
    settings.save_require_signed_packages(False)
    unsigned = verify(make_package(tmp_path / "a", key=None))
    assert unsigned.signed is False
    refused(make_package(tmp_path / "b", key=OTHER), "sig_bad")


def test_a_damaged_settings_file_keeps_the_signature_required(tmp_path: Path, isolated_settings: Path) -> None:
    isolated_settings.write_text("[1, 2", encoding="utf-8")
    assert settings.get_require_signed_packages() is True
    refused(make_package(tmp_path, key=None), "sig_missing")


def test_the_environment_can_only_turn_the_requirement_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings.save_require_signed_packages(False)
    monkeypatch.setenv(package_release.REQUIRE_SIGNED_PACKAGES_ENV, "1")
    refused(make_package(tmp_path, key=None), "sig_missing")


def test_a_signature_by_another_key_is_refused(tmp_path: Path) -> None:
    refused(make_package(tmp_path, key=OTHER), "sig_bad")


def test_a_signature_made_for_another_project_or_version_cannot_be_reused(tmp_path: Path) -> None:
    refused(make_package(tmp_path / "p", sign_as=("OTHER", "1.2.0")), "sig_bad")
    refused(make_package(tmp_path / "v", sign_as=("DEMO", "1.1.0")), "sig_bad")


def test_a_signature_of_another_domain_is_refused(tmp_path: Path) -> None:
    package = make_package(tmp_path, key=None)
    digest = package_release.file_sha256(package)
    wrong = KEY.sign(f"hydra-pkg/1|DEMO|1.2.0|{digest}".encode()).hex()  # the prefix of the packages of the device
    package.with_name(package.name + ".sig").write_text(wrong, encoding="ascii")
    refused(package, "sig_bad")


def test_a_malformed_signature_is_refused(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    package.with_name(package.name + ".sig").write_text("zz", encoding="ascii")
    refused(package, "sig_bad")


def test_a_package_changed_after_publication_is_refused(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    package.write_bytes(package.read_bytes() + b"\0")
    refused(package, "sha256_bad")


def test_the_sha256_file_is_required(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    package.with_name(package.name + ".sha256").unlink()
    refused(package, "sha256_missing")


def test_a_name_that_is_not_a_package_name_is_refused(tmp_path: Path) -> None:
    other = tmp_path / "notes.tgz"
    other.write_bytes(b"x")
    refused(other, "name_bad")


@pytest.mark.parametrize("member", ["../escape.txt", "/abs.txt", "a\\b.txt", "C:evil.txt", ".git/config", "ok/../../x"])
def test_members_that_could_leave_the_target_are_refused(tmp_path: Path, member: str) -> None:
    refused(make_package(tmp_path, members={member: b"x"}), "member_bad")


def test_links_are_refused(tmp_path: Path) -> None:
    def add_link(tar: tarfile.TarFile) -> None:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tar.addfile(link)

    refused(make_package(tmp_path, extra=add_link), "member_bad")


def test_the_unpacked_size_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(package_release, "MAX_UNPACKED_BYTES", 10)
    refused(make_package(tmp_path), "too_big")


# ---- installing ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def test_install_puts_the_package_in_the_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    result = install_package(make_package(tmp_path / "dl"), ws, public_key_hex=PUBLIC)
    assert result.signed and (ws / "DEMO" / "src" / "app.py").read_text() == "print(1)\n"
    assert not [p for p in ws.iterdir() if p.name.startswith(".")]


def test_install_keeps_the_previous_folder_as_a_backup_and_refuses_the_same_or_an_older_version(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    install_package(make_package(tmp_path / "a", version="1.2.0"), ws, public_key_hex=PUBLIC)
    install_package(make_package(tmp_path / "b", version="1.3.0"), ws, public_key_hex=PUBLIC)
    assert json.loads((ws / "DEMO" / "hydra-umc.project.json").read_text())["version"] == "1.3.0"
    assert len([p for p in ws.iterdir() if p.name.startswith("DEMO.backup-")]) == 1
    for old in ("1.3.0", "1.1.0"):
        with pytest.raises(PackageError) as caught:
            install_package(make_package(tmp_path / old, version=old), ws, public_key_hex=PUBLIC)
        assert caught.value.code == "not_newer"
    assert json.loads((ws / "DEMO" / "hydra-umc.project.json").read_text())["version"] == "1.3.0"


def test_install_refuses_a_manifest_that_names_another_version(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    bad = make_package(tmp_path / "dl", members={"hydra-umc.project.json": manifest("9.9.9")})
    with pytest.raises(PackageError) as caught:
        install_package(bad, ws, public_key_hex=PUBLIC)
    assert caught.value.code == "manifest_bad"
    assert list(ws.iterdir()) == []


def test_install_does_nothing_when_the_package_is_not_signed(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    with pytest.raises(PackageError):
        install_package(make_package(tmp_path / "dl", key=None), ws, public_key_hex=PUBLIC)
    assert list(ws.iterdir()) == []


# ---- download of the assets of a release -----------------------------------------------------------------------------------------------------------------------------------


def info_with(assets: dict[str, str]) -> release_channel.ReleaseInfo:
    return release_channel.ReleaseInfo("DEMO", "v1.2.0", "1.2.0", False, True, "a" * 40, assets)


def test_the_three_files_of_the_release_are_downloaded(tmp_path: Path) -> None:
    source = make_package(tmp_path / "src")
    base = "https://github.com/JuanenRac/DEMO/releases/download/v1.2.0/"
    assets = {f"{source.name}{suffix}": base + source.name + suffix for suffix in ("", ".sha256", ".sig")}
    asked: list[str] = []

    def download(url: str, destination: Path, limit: int) -> None:
        asked.append(url)
        destination.write_bytes((source.parent / destination.name).read_bytes())

    target = tmp_path / "dl"
    target.mkdir()
    got = fetch_release_package(info_with(assets), target, download=download)
    assert len(asked) == 3 and verify(got).signed


def test_a_release_without_the_package_or_from_another_host_is_refused(tmp_path: Path) -> None:
    with pytest.raises(PackageError) as caught:
        fetch_release_package(info_with({}), tmp_path, download=lambda *a: None)
    assert caught.value.code == "no_asset"
    with pytest.raises(PackageError) as caught:
        fetch_release_package(info_with({"DEMO-1.2.0.tgz": "https://example.invalid/x.tgz"}), tmp_path, download=lambda *a: None)
    assert caught.value.code == "download_failed"


def test_a_failed_download_is_a_clear_refusal(tmp_path: Path) -> None:
    def broken(url: str, destination: Path, limit: int) -> None:
        raise OSError("connection reset")

    with pytest.raises(PackageError) as caught:
        fetch_release_package(info_with({"DEMO-1.2.0.tgz": "https://github.com/JuanenRac/DEMO/x.tgz"}), tmp_path, download=broken)
    assert caught.value.code == "download_failed"


# ---- the command and the tool of the publisher -----------------------------------------------------------------------------------------------------------------------


def run_cli(monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr("sys.argv", ["prog", "--cli", *argv])
    return main_module.main()


def test_package_verify_command_speaks_the_language_and_exits_with_the_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(package_release, "RELEASES_PUBLIC_KEY", PUBLIC)
    good = make_package(tmp_path / "ok")
    assert run_cli(monkeypatch, "package", "verify", str(good), "--lang", "es") == 0
    assert "firmado" in capsys.readouterr().out
    bad = make_package(tmp_path / "bad", key=None)
    assert run_cli(monkeypatch, "package", "verify", str(bad), "--lang", "pt") == 1
    err = capsys.readouterr().err
    assert "nunca é instalado" in err and "não foi instalado nada" in err


def test_package_install_by_project_name_downloads_the_latest_stable_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(package_release, "RELEASES_PUBLIC_KEY", PUBLIC)
    source = make_package(tmp_path / "src")
    base = "https://github.com/JuanenRac/DEMO/releases/download/v1.2.0/"
    item = {"tag_name": "v1.2.0", "draft": False, "prerelease": False,
            "assets": [{"name": source.name + s, "browser_download_url": base + source.name + s} for s in ("", ".sha256", ".sig")]}

    def fetch(url: str):
        return [item] if "/releases?" in url else {"object": {"type": "commit", "sha": "a" * 40}}

    def download(url: str, destination: Path, limit: int) -> None:
        destination.write_bytes((source.parent / destination.name).read_bytes())

    monkeypatch.setattr(release_channel, "fetch_json", fetch)
    monkeypatch.setattr(package_release, "download_to_file", download)
    ws = tmp_path / "ws"
    ws.mkdir()
    assert run_cli(monkeypatch, "package", "install", "DEMO", "--workspace", str(ws), "--lang", "en") == 0
    assert (ws / "DEMO" / "src" / "app.py").is_file()
    assert "Installed DEMO 1.2.0" in capsys.readouterr().out


def test_package_install_without_network_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def offline(url: str):
        raise OSError("offline")

    monkeypatch.setattr(release_channel, "fetch_json", offline)
    ws = tmp_path / "ws"
    ws.mkdir()
    assert run_cli(monkeypatch, "package", "install", "DEMO", "--workspace", str(ws), "--lang", "de") == 1
    assert "Es wurde nichts installiert" in capsys.readouterr().err
    assert list(ws.iterdir()) == []


def test_the_tool_of_the_publisher_refuses_a_key_that_is_not_the_pinned_one(tmp_path: Path) -> None:
    package = make_package(tmp_path, key=None)
    with pytest.raises(SystemExit):
        package_pc_release.sign(package, OTHER)  # not the pinned key: nothing is written
    assert not package.with_name(package.name + ".sig").exists()


def test_the_tool_of_the_publisher_signs_what_the_updater_verifies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(package_release, "RELEASES_PUBLIC_KEY", PUBLIC)
    package = make_package(tmp_path, key=None)
    sig = package_pc_release.sign(package, KEY)
    assert sig.is_file() and verify(package).signed
    # the key file is read from the place the environment names and its content is never printed
    pem = tmp_path / "k.pem"
    pem.write_bytes(KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    monkeypatch.setenv("HYDRA_RELEASE_KEY", str(pem))
    sig.unlink()
    package_pc_release.sign(package)
    assert verify(package).signed


def test_pack_makes_the_package_and_its_hash_from_a_tag(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "DEMO"
    repo.mkdir()
    (repo / "hydra-umc.project.json").write_bytes(manifest("1.2.0"))
    for command in (["init", "-q", "-b", "main"], ["add", "."], ["-c", "user.email=a@b.invalid", "-c", "user.name=t", "commit", "-qm", "x"], ["tag", "v1.2.0"]):
        subprocess.run(["git", *command], cwd=repo, check=True, capture_output=True)
    package = package_pc_release.pack(repo, "v1.2.0", tmp_path / "out")
    assert package.name == "DEMO-1.2.0.tgz"
    assert package.with_name(package.name + ".sha256").read_text().startswith(package_release.file_sha256(package))
    with tarfile.open(package) as tar:
        assert "hydra-umc.project.json" in tar.getnames()
