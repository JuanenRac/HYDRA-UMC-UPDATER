# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_model_bundle.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""`package verify|install` of a signed bundle of compiled models. The keys are made by the test and no network is used. When the checkout of the detection
service sits next to this one, bundles made by its own `make_bundle` are installed here too, and what its `apply_bundle` refuses is refused here."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402

from hydra_umc_updater import i18n, model_bundle, settings  # noqa: E402
from hydra_umc_updater import main as main_module  # noqa: E402
from hydra_umc_updater.package_release import PackageError  # noqa: E402

KEY = ed25519.Ed25519PrivateKey.generate()
OTHER = ed25519.Ed25519PrivateKey.generate()


def raw_public(key: ed25519.Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entry(name: str, version: str, data: bytes, channel: str = "stable") -> dict:
    result = {"name": name, "version": version, "task": "detection", "input_shape": [640, 640, 3], "classes": ["a"], "hef_path": f"{name}-{version}.hef",
              "sha256": sha(data), "hailo_arch": "hailo8"}
    if channel != "stable":
        result["channel"] = channel
    return result


def make_zip(path: Path, members: dict[str, bytes], listing: dict[str, str] | None = None, *, bundle_json: bytes | None = None) -> Path:
    listed = {name: sha(data) for name, data in sorted(members.items())} if listing is None else listing
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bundle.json", bundle_json if bundle_json is not None else json.dumps({"format": 1, "files": listed}))
        for name, data in sorted(members.items()):
            archive.writestr(name, data)
    return path


def signed_members(entries: list[dict], files: dict[str, bytes], signer: ed25519.Ed25519PrivateKey = KEY) -> dict[str, bytes]:
    registry = json.dumps(entries, indent=2).encode()
    members = {"registry.json": registry, "registry.json.sig": (signer.sign(registry).hex() + "\n").encode()}
    members.update({"models/" + name: data for name, data in files.items()})
    return members


def bundle(tmp_path: Path, entries: list[dict], files: dict[str, bytes], signer: ed25519.Ed25519PrivateKey = KEY, name: str = "models.zip") -> Path:
    return make_zip(tmp_path / name, signed_members(entries, files, signer))


@pytest.fixture
def key_file(tmp_path: Path) -> Path:
    path = tmp_path / "owner.pub"
    path.write_text(raw_public(KEY).hex() + "\n", encoding="ascii")
    return path


@pytest.fixture
def node(tmp_path: Path) -> tuple[Path, Path]:
    models = tmp_path / "node" / "models"
    models.mkdir(parents=True)
    return tmp_path / "node" / "registry.json", models


@pytest.fixture
def on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(model_bundle.MODEL_BUNDLES_ENV, "1")


HEF1, HEF2 = b"first model", b"second model, newer"
V1 = [entry("det", "1.0.0", HEF1)]
V2 = [entry("det", "1.1.0", HEF2)]


class TestSwitch:
    def test_off_by_default_and_nothing_is_written(self, tmp_path, key_file, node):
        registry, models = node
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
        assert caught.value.code == "models_off"
        assert not registry.exists() and not list(models.iterdir())

    @pytest.mark.parametrize("value", ["0", "", "no", "off", "maybe"])
    def test_other_words_do_not_switch_it_on(self, monkeypatch, value):
        monkeypatch.setenv(model_bundle.MODEL_BUNDLES_ENV, value)
        assert model_bundle.enabled() is False

    def test_the_saved_setting_switches_it_on_only_with_a_real_true(self, isolated_settings):
        assert model_bundle.enabled() is False
        for wrong in ("true", 1, "yes", None):
            settings.save_settings(model_bundles=wrong)
            assert model_bundle.enabled() is False
        settings.save_model_bundles(True)
        assert model_bundle.enabled() is True

    def test_a_damaged_settings_file_keeps_it_off(self, isolated_settings):
        isolated_settings.write_text("{not json", encoding="utf-8")
        assert settings.get_model_bundles() is False

    def test_verify_needs_no_switch(self, tmp_path, key_file):
        result = model_bundle.verify_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), key_file)
        assert result.models == ("det 1.0.0",)


class TestInstall:
    def test_a_first_install_puts_the_models_and_the_signed_registry_in_place(self, tmp_path, key_file, node, on):
        registry, models = node
        result = model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
        assert result.models == ("det 1.0.0",) and result.files == ("models/det-1.0.0.hef",)
        assert (models / "det-1.0.0.hef").read_bytes() == HEF1
        assert json.loads(registry.read_text())[0]["version"] == "1.0.0"
        assert KEY.public_key().verify(bytes.fromhex(registry.with_name("registry.json.sig").read_text().strip()), registry.read_bytes()) is None
        assert not list(registry.parent.glob("*.part")) and not list(models.glob("*.part")) and not registry.with_name("registry.json.lock").exists()

    def test_an_update_keeps_the_previous_registry_and_signature(self, tmp_path, key_file, node, on):
        registry, models = node
        model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
        first = registry.read_bytes()
        model_bundle.install_bundle(bundle(tmp_path, V1 + V2, {"det-1.0.0.hef": HEF1, "det-1.1.0.hef": HEF2}, name="b2.zip"), registry, models, key_file)
        assert registry.with_name("registry.json.prev").read_bytes() == first
        assert registry.with_name("registry.json.sig.prev").is_file()
        assert (models / "det-1.1.0.hef").read_bytes() == HEF2

    def test_a_downgrade_is_refused_untouched_and_allowed_on_request(self, tmp_path, key_file, node, on):
        registry, models = node
        model_bundle.install_bundle(bundle(tmp_path, V2, {"det-1.1.0.hef": HEF2}), registry, models, key_file)
        before = registry.read_bytes()
        older = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}, name="older.zip")
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(older, registry, models, key_file)
        assert caught.value.code == "models_downgrade" and caught.value.params["installed"] == "1.1.0"
        assert registry.read_bytes() == before and not (models / "det-1.0.0.hef").exists()
        model_bundle.install_bundle(older, registry, models, key_file, allow_downgrade=True)
        assert json.loads(registry.read_text())[0]["version"] == "1.0.0"

    def test_a_registry_that_drops_a_model_is_refused_like_a_downgrade(self, tmp_path, key_file, node, on):
        registry, models = node
        model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
        other = [entry("pose", "1.0.0", b"pose")]
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(bundle(tmp_path, other, {"pose-1.0.0.hef": b"pose"}, name="p.zip"), registry, models, key_file)
        assert caught.value.code == "models_lost" and caught.value.params["model"] == "det"

    def test_a_channel_counts_on_its_own(self, tmp_path, key_file, node, on):
        registry, models = node
        stable = [entry("det", "2.0.0", b"s2")]
        model_bundle.install_bundle(bundle(tmp_path, stable, {"det-2.0.0.hef": b"s2"}), registry, models, key_file)
        canary = stable + [entry("det", "1.5.0", b"c", "canary")]
        model_bundle.install_bundle(bundle(tmp_path, canary, {"det-2.0.0.hef": b"s2", "det-1.5.0.hef": b"c"}, name="c.zip"), registry, models, key_file)
        assert len(json.loads(registry.read_text())) == 2

    def test_a_held_lock_is_a_refusal_not_a_hang(self, tmp_path, key_file, node, on, monkeypatch):
        registry, models = node
        registry.with_name("registry.json.lock").write_text("held")
        monkeypatch.setattr(model_bundle.time, "sleep", lambda _s: setattr(model_bundle.time, "monotonic", lambda: 1e12))
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
        assert caught.value.code == "models_install_failed"
        assert not registry.exists()


class TestRefusals:
    """Each refusal happens before the first file is written."""

    def refuse(self, path, key_file, node, code):
        registry, models = node
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(path, registry, models, key_file)
        assert caught.value.code == code
        assert not registry.exists() and not list(models.iterdir())

    def test_no_public_key(self, tmp_path, node, on):
        self.refuse_key = None
        registry, models = node
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, None)
        assert caught.value.code == "models_needs_key"

    def test_a_bad_key_file(self, tmp_path, node, on):
        bad = tmp_path / "bad.pub"
        for content in (b"", b"zz", b"\x00" * 31, b"ab" * 31):
            bad.write_bytes(content)
            self.refuse(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), bad, node, "models_key_bad")
        self.refuse(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), tmp_path / "missing.pub", node, "models_key_bad")

    def test_the_raw_key_form_works(self, tmp_path, node, on):
        raw = tmp_path / "raw.pub"
        raw.write_bytes(raw_public(KEY))
        assert model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), *node, raw).models == ("det 1.0.0",)

    def test_a_signature_by_another_key(self, tmp_path, key_file, node, on):
        self.refuse(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}, signer=OTHER), key_file, node, "models_sig_bad")

    def test_a_registry_changed_after_signing(self, tmp_path, key_file, node, on):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1})
        members["registry.json"] = json.dumps(V2).encode()
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_sig_bad")

    @pytest.mark.parametrize("signature", [b"", b"nothex", b"ab" * 10, b"ab" * 64 + b"00"])
    def test_a_signature_that_is_not_64_bytes(self, tmp_path, key_file, node, on, signature):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1})
        members["registry.json.sig"] = signature
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_sig_bad")

    def test_a_model_changed_in_the_zip_with_its_listing_fixed(self, tmp_path, key_file, node, on):
        members = signed_members(V1, {"det-1.0.0.hef": b"swapped"})
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_hef_bad")

    def test_a_model_changed_after_the_listing(self, tmp_path, key_file, node, on):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1})
        listing = {name: sha(data) for name, data in members.items()}
        members["models/det-1.0.0.hef"] = b"swapped"
        self.refuse(make_zip(tmp_path / "x.zip", members, listing), key_file, node, "models_hash_bad")

    def test_a_file_the_registry_does_not_name(self, tmp_path, key_file, node, on):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1, "extra.hef": b"x"})
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_hef_bad")

    def test_a_file_missing_from_the_listing_or_the_zip(self, tmp_path, key_file, node, on):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1})
        listing = {name: sha(data) for name, data in members.items() if name != "models/det-1.0.0.hef"}
        self.refuse(make_zip(tmp_path / "a.zip", members, listing), key_file, node, "models_hash_bad")
        listing = {name: sha(data) for name, data in members.items()}
        listing["models/ghost.hef"] = sha(b"x")
        self.refuse(make_zip(tmp_path / "b.zip", members, listing), key_file, node, "models_hash_bad")

    @pytest.mark.parametrize("name", ["../evil.hef", "/abs.hef", "models/../x", "models//x", "notes.txt", "models", "C:/x"])
    def test_members_that_are_not_allowed(self, tmp_path, key_file, node, on, name):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1})
        members[name] = b"x"
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_member_bad")

    @pytest.mark.parametrize("name", ["models\\x", "a\\b", "", "m" * 301, "models/a\x00b"])
    def test_names_the_check_refuses_even_if_a_zip_writer_would_normalise_them(self, name):
        assert model_bundle._member_ok(name) is False

    def test_a_repeated_member(self, tmp_path, key_file, node, on):
        path = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1})
        with zipfile.ZipFile(path, "a") as archive:
            with pytest.warns(UserWarning):
                archive.writestr("registry.json", b"[]")
        self.refuse(path, key_file, node, "models_member_bad")

    def test_bundle_json_missing_or_wrong(self, tmp_path, key_file, node, on):
        members = signed_members(V1, {"det-1.0.0.hef": HEF1})
        with zipfile.ZipFile(tmp_path / "none.zip", "w") as archive:
            for name, data in members.items():
                archive.writestr(name, data)
        self.refuse(tmp_path / "none.zip", key_file, node, "models_format_bad")
        for text in (b"not json", b"[]", json.dumps({"format": 2, "files": {}}).encode(), json.dumps({"format": 1}).encode(), json.dumps({"format": 1, "files": []}).encode()):
            self.refuse(make_zip(tmp_path / "w.zip", members, bundle_json=text), key_file, node, "models_format_bad")

    def test_no_registry_or_no_signature(self, tmp_path, key_file, node, on):
        for dropped in ("registry.json", "registry.json.sig"):
            members = signed_members(V1, {"det-1.0.0.hef": HEF1})
            del members[dropped]
            self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_format_bad")

    def test_not_a_zip_and_not_there(self, tmp_path, key_file, node, on):
        (tmp_path / "junk.zip").write_bytes(b"this is not a zip")
        self.refuse(tmp_path / "junk.zip", key_file, node, "models_unreadable")
        self.refuse(tmp_path / "missing.zip", key_file, node, "models_unreadable")

    def test_too_many_members(self, tmp_path, key_file, node, on, monkeypatch):
        monkeypatch.setattr(model_bundle, "MAX_MEMBERS", 3)
        self.refuse(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), key_file, node, "models_limits")

    def test_too_large_unpacked(self, tmp_path, key_file, node, on, monkeypatch):
        monkeypatch.setattr(model_bundle, "MAX_TOTAL_BYTES", 10)
        self.refuse(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), key_file, node, "models_limits")

    @pytest.mark.parametrize("registry", [b"not json", b"{}", b"[1]", b'[{"name": "a"}]',
                                          json.dumps([{**V1[0], "version": "1.0"}]).encode(),
                                          json.dumps([{**V1[0], "channel": "beta"}]).encode(),
                                          json.dumps([{**V1[0], "sha256": "xyz"}]).encode(),
                                          json.dumps([{**V1[0], "name": ""}]).encode()])
    def test_a_registry_that_is_not_a_registry(self, tmp_path, key_file, node, on, registry):
        members = {"registry.json": registry, "registry.json.sig": (KEY.sign(registry).hex()).encode()}
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_registry_bad")

    def test_a_registry_path_that_leaves_the_models_folder(self, tmp_path, key_file, node, on):
        evil = [{**V1[0], "hef_path": "../escape.hef"}]
        members = signed_members(evil, {})
        members["models/../escape.hef"] = HEF1
        self.refuse(make_zip(tmp_path / "x.zip", members), key_file, node, "models_member_bad")

    def test_an_installed_registry_that_is_damaged_stops_the_update(self, tmp_path, key_file, node, on):
        registry, models = node
        registry.write_text("{broken", encoding="utf-8")
        with pytest.raises(PackageError) as caught:
            model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
        assert caught.value.code == "models_registry_bad"
        assert not list(models.iterdir())
        model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file, allow_downgrade=True)


class TestCommandLine:
    @pytest.fixture(autouse=True)
    def _monkeypatch(self, monkeypatch):
        self.monkeypatch = monkeypatch

    def run(self, capsys, *argv):
        self.monkeypatch.setattr("sys.argv", ["prog", "--cli", "package", *argv])
        code = main_module.main()
        out = capsys.readouterr()
        return code, out.out, out.err

    def test_verify_reads_only(self, tmp_path, key_file, capsys):
        path = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1})
        code, out, err = self.run(capsys, "verify", str(path), "--public-key", str(key_file), "--lang", "en")
        assert code == 0 and "1 model(s), signed" in out and not err

    def test_install_off_by_default(self, tmp_path, key_file, node, capsys):
        registry, models = node
        path = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1})
        code, out, err = self.run(capsys, "install", str(path), "--public-key", str(key_file), "--models-registry", str(registry), "--models-dir", str(models), "--lang", "en")
        assert code == 1 and "is off" in err and "nothing was installed" in err and not registry.exists()

    def test_install_needs_the_two_paths(self, tmp_path, key_file, on, capsys):
        path = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1})
        code, out, err = self.run(capsys, "install", str(path), "--public-key", str(key_file), "--lang", "en")
        assert code == 1 and "--models-registry" in err

    def test_install_and_json(self, tmp_path, key_file, node, on, capsys):
        registry, models = node
        path = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1})
        code, out, err = self.run(capsys, "install", str(path), "--public-key", str(key_file), "--models-registry", str(registry), "--models-dir", str(models), "--json")
        assert code == 0 and json.loads(out)["models"] == ["det 1.0.0"] and (models / "det-1.0.0.hef").is_file()

    def test_the_downgrade_flag(self, tmp_path, key_file, node, on, capsys):
        registry, models = node
        common = ["--public-key", str(key_file), "--models-registry", str(registry), "--models-dir", str(models), "--lang", "en"]
        assert self.run(capsys, "install", str(bundle(tmp_path, V2, {"det-1.1.0.hef": HEF2})), *common)[0] == 0
        older = str(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}, name="o.zip"))
        code, _out, err = self.run(capsys, "install", older, *common)
        assert code == 1 and "1.1.0" in err and "--allow-downgrade" in err
        assert self.run(capsys, "install", older, *common, "--allow-downgrade")[0] == 0

    def test_a_tgz_still_goes_the_old_way(self, tmp_path, capsys):
        code, _out, err = self.run(capsys, "verify", str(tmp_path / "nope-1.0.0.tgz"), "--lang", "en")
        assert code == 1 and "ERROR" in err


class TestTranslations:
    CODES = ["models_off", "models_needs_key", "models_needs_paths", "models_key_bad", "models_unreadable", "models_limits", "models_member_bad", "models_format_bad",
             "models_hash_bad", "models_sig_bad", "models_registry_bad", "models_hef_bad", "models_downgrade", "models_lost", "models_install_failed", "models_ok",
             "models_installed"]

    def test_every_message_is_in_the_eight_languages(self):
        for code in self.CODES:
            for language in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
                assert "pkg_" + code in i18n.TRANSLATIONS[language], (language, code)

    def test_the_blanks_are_the_same_in_every_language(self):
        import string

        for code in self.CODES:
            reference = {f for _t, f, _s, _c in string.Formatter().parse(i18n.TRANSLATIONS["en"]["pkg_" + code]) if f}
            for language in ("es", "de", "fr", "it", "ja", "zh", "pt"):
                found = {f for _t, f, _s, _c in string.Formatter().parse(i18n.TRANSLATIONS[language]["pkg_" + code]) if f}
                assert found == reference, (language, code)

    def test_every_refusal_the_module_raises_has_a_message(self):
        source = (Path(model_bundle.__file__)).read_text(encoding="utf-8")
        import re

        raised = set(re.findall(r'PackageError\(\s*"(models_[a-z_]+)"', source))
        assert raised <= set(self.CODES), raised - set(self.CODES)


detection_checkout = Path(__file__).resolve().parents[2] / "HYDRA-UMC-DETECTION-HEF" / "src"


@pytest.mark.skipif(not detection_checkout.is_dir(), reason="the checkout of the detection service is not next to this repository")
class TestAgainstTheDetectionService:
    @pytest.fixture(autouse=True)
    def service(self):
        sys.path.insert(0, str(detection_checkout))
        try:
            import hydra_umc_detection_hef.bundle as service_bundle
            import hydra_umc_detection_hef.registry as service_registry
        except ImportError:
            pytest.skip("the detection service does not import here")
        self.bundle_module, self.registry_module = service_bundle, service_registry
        yield
        sys.path.remove(str(detection_checkout))

    def build(self, tmp_path, entries, files):
        models = tmp_path / "build" / "models"
        models.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (models / name).write_bytes(data)
        registry = tmp_path / "build" / "registry.json"
        registry.write_text(json.dumps(entries), encoding="utf-8")
        registry.with_name("registry.json.sig").write_text(KEY.sign(registry.read_bytes()).hex() + "\n", encoding="ascii")
        out = tmp_path / "service.zip"
        self.bundle_module.make_bundle(registry, models, out)
        return out

    def test_a_bundle_the_service_makes_installs_here_and_the_service_accepts_the_result(self, tmp_path, key_file, node, on):
        registry, models = node
        path = self.build(tmp_path, V1, {"det-1.0.0.hef": HEF1})
        model_bundle.install_bundle(path, registry, models, key_file)
        assert self.registry_module.load_registry(registry, key_file)[0].version == "1.0.0"
        assert (models / "det-1.0.0.hef").read_bytes() == HEF1

    def test_both_sides_refuse_the_same_downgrade(self, tmp_path, key_file, node, on):
        registry, models = node
        model_bundle.install_bundle(self.build(tmp_path, V2, {"det-1.1.0.hef": HEF2}), registry, models, key_file)
        older = self.build(tmp_path / "older", V1, {"det-1.0.0.hef": HEF1}) if (tmp_path / "older").mkdir() is None else None
        with pytest.raises(PackageError):
            model_bundle.install_bundle(older, registry, models, key_file)
        with pytest.raises(self.bundle_module.BundleError):
            self.bundle_module.apply_bundle(older, registry, models, key_file, enabled=True)
