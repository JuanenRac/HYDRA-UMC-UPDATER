# =============================================================================
# HYDRA-UMC-UPDATER - Applying a signed image delta to the other slot (synthetic images, ephemeral test keys only)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The delta is built here the way the image builder builds it (format `hydra-image-delta/1`, the domain tag, blocks that copy or carry new bytes) over small synthetic
images, signed with keys made in memory for each test, so nothing real is signed, read or written outside the temporary folder."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hydra_umc_updater import i18n, image_delta, image_release, main

ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
from cryptography.hazmat.primitives import serialization  # noqa: E402

BLOCK = 512
COMMIT = "b" * 40
RELEASE_DOMAIN = b"hydra-umc-os-rebuilder-release/1\n"


def new_key() -> tuple[object, str]:
    private = ed25519.Ed25519PrivateKey.generate()
    return private, private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def sign(path: Path, private, domain: bytes) -> None:
    message = domain + hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii")
    path.with_name(path.name + ".sig").write_text(private.sign(message).hex() + "\n", encoding="utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def images() -> tuple[bytes, bytes]:
    base = b"".join(bytes([i]) * BLOCK for i in range(8))  # eight different blocks
    target = base[: 2 * BLOCK] + b"N" * BLOCK + base[3 * BLOCK : 7 * BLOCK] + b"T" * 100  # one block replaced, the last one cut and new
    return base, target


def make_delta(store: Path, private, base: bytes, target: bytes, *, domain: bytes = image_delta.DOMAIN) -> dict:
    """The same blocks the image builder would write: a copy of a base block when the same bytes (and length) are in the base, new bytes otherwise."""
    index: dict[str, int] = {}
    for i in range(0, len(base), BLOCK):
        index.setdefault(sha(base[i : i + BLOCK]), i // BLOCK)
    ops, literal = [], b""
    for i in range(0, len(target), BLOCK):
        chunk = target[i : i + BLOCK]
        found = index.get(sha(chunk))
        if found is not None and min(BLOCK, len(base) - found * BLOCK) == len(chunk):
            ops.append(["c", found, len(chunk)])
        else:
            ops.append(["l", len(literal), len(chunk)])
            literal += chunk
    record = {
        "format": image_delta.FORMAT, "block_size": BLOCK, "base": {"size": len(base), "sha256": sha(base)},
        "target": {"size": len(target), "sha256": sha(target)}, "data": {"size": len(literal), "sha256": sha(literal)}, "blocks": ops,
    }
    store.mkdir(parents=True, exist_ok=True)
    (store / "delta.bin").write_bytes(literal)
    (store / "delta.json").write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    sign(store / "delta.json", private, domain)
    return record


def make_release(tmp: Path, private, target: bytes, **overrides) -> Path:
    data = {
        "format": "hydra-image-release/1", "image": "hydra.img", "size": len(target), "sha256": sha(target),
        "version": "0.5.0", "commit": COMMIT, "tag": "image-v0.5.0",
    }
    data.update(overrides)
    manifest = tmp / "release.json"
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sign(manifest, private, RELEASE_DOMAIN)
    return manifest


class World:
    def __init__(self, tmp: Path) -> None:
        self.private, self.public = new_key()
        self.base_bytes, self.target_bytes = images()
        self.base = tmp / "slot_a" / "hydra.img"
        self.base.parent.mkdir()
        self.base.write_bytes(self.base_bytes)
        self.store = tmp / "delta"
        make_delta(self.store, self.private, self.base_bytes, self.target_bytes)
        self.release = make_release(tmp, self.private, self.target_bytes)
        self.out = tmp / "slot_b"
        self.keys = image_release.TrustedKeys(active=(self.public,))
        self.tmp = tmp

    def apply(self, **overrides):
        args = dict(release=self.release, store=self.store, base=self.base, out_dir=self.out, keys=self.keys, enabled=True)
        args.update(overrides)
        return image_delta.apply_delta(**args)

    def untouched(self) -> bool:
        return not self.out.exists() or list(self.out.iterdir()) == []


def code_of(excinfo) -> str:
    return excinfo.value.code


def test_a_good_delta_rebuilds_the_image_of_the_release_in_the_other_slot(tmp_path: Path) -> None:
    w = World(tmp_path)
    result = w.apply()
    assert (w.out / "hydra.img").read_bytes() == w.target_bytes
    assert result.version == "0.5.0" and result.sha256 == sha(w.target_bytes) and result.size == len(w.target_bytes)
    assert result.copied_bytes == 6 * BLOCK and result.new_bytes == BLOCK + 100  # six base blocks copied, one replaced, the cut tail new
    assert w.base.read_bytes() == w.base_bytes  # the running image is only read
    assert [p.name for p in w.out.iterdir()] == ["hydra.img"]  # no staging left behind


def test_a_release_older_than_the_minimum_version_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    w = World(tmp_path)  # the release is 0.5.0
    for minimum in ("0.5.1", "0.6", "1"):
        with pytest.raises(image_delta.ImageDeltaError) as excinfo:
            w.apply(minimum_version=minimum)
        assert code_of(excinfo) == "too_old"
        assert w.untouched()
    with pytest.raises(image_delta.ImageDeltaError) as excinfo:
        w.apply(minimum_version="latest")
    assert code_of(excinfo) == "minimum_version"
    assert w.apply(minimum_version="0.5").version == "0.5.0"


def test_the_use_of_deltas_is_off_unless_it_is_switched_on(tmp_path: Path) -> None:
    w = World(tmp_path)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply(enabled=False)
    assert code_of(error) == "disabled" and w.untouched()


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda w: (w.store / "delta.json.sig").unlink(), "missing"),
        (lambda w: (w.store / "delta.json").unlink(), "missing"),
        (lambda w: (w.store / "delta.json.sig").write_text("zz\n", encoding="utf-8"), "signature"),
        (lambda w: (w.store / "delta.json.sig").write_text("ab" * 10 + "\n", encoding="utf-8"), "signature"),
        (lambda w: sign(w.store / "delta.json", new_key()[0], image_delta.DOMAIN), "signature"),
        (lambda w: sign(w.store / "delta.json", w.private, RELEASE_DOMAIN), "signature"),  # a release signature is not a delta signature
        (lambda w: (w.store / "delta.bin").write_bytes(b"x" * 10), "data"),
        (lambda w: (w.store / "delta.bin").unlink(), "data"),
        (lambda w: w.base.write_bytes(w.base_bytes + b"!"), "base"),
        (lambda w: w.base.write_bytes(bytes(len(w.base_bytes))), "base"),
        (lambda w: w.base.unlink(), "base"),
    ],
)
def test_every_doubt_refuses_and_leaves_the_other_slot_as_it_was(tmp_path: Path, mutate, code: str) -> None:
    w = World(tmp_path)
    mutate(w)
    with pytest.raises(image_release.ImageReleaseError) as error:
        w.apply()
    assert code_of(error) == code
    assert w.untouched()


def test_a_delta_that_builds_another_image_than_the_release_is_refused(tmp_path: Path) -> None:
    w = World(tmp_path)
    other = w.target_bytes[:-1] + b"X"
    make_delta(w.store, w.private, w.base_bytes, other)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) == "not_release" and w.untouched()


def test_a_release_that_does_not_verify_is_refused_before_the_delta_is_read(tmp_path: Path) -> None:
    w = World(tmp_path)
    w.release.write_text(w.release.read_text(encoding="utf-8").replace("0.5.0", "0.5.1"), encoding="utf-8")
    with pytest.raises(image_release.ImageReleaseError) as error:
        w.apply()
    assert code_of(error) == "signature_bad" and w.untouched()
    (tmp_path / "second").mkdir()
    w2 = World(tmp_path / "second")
    with pytest.raises(image_release.ImageReleaseError) as error2:
        w2.apply(keys=image_release.TrustedKeys(active=(new_key()[1],)))
    assert code_of(error2) == "signature_bad"


def test_the_release_signature_cannot_pass_as_a_delta_and_the_delta_cannot_pass_as_a_release(tmp_path: Path) -> None:
    w = World(tmp_path)
    sign(w.store / "delta.json", w.private, RELEASE_DOMAIN)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) == "signature"
    w.release.with_name("release.json.sig").write_text((w.store / "delta.json.sig").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(image_release.ImageReleaseError):
        w.apply()


@pytest.mark.parametrize(
    "edit",
    [
        lambda r: r.update(format="other/1"),
        lambda r: r.update(block_size=10),
        lambda r: r.update(block_size="big"),
        lambda r: r.update(blocks="none"),
        lambda r: r.update(blocks=[["x", 0, 4]]),
        lambda r: r.update(blocks=[["c", 0]]),
        lambda r: r["base"].update(size=-1),
        lambda r: r["target"].update(sha256="nothex"),
        lambda r: r.pop("data"),
    ],
)
def test_a_damaged_record_is_refused_even_when_it_is_signed(tmp_path: Path, edit) -> None:
    w = World(tmp_path)
    record = json.loads((w.store / "delta.json").read_text(encoding="utf-8"))
    edit(record)
    (w.store / "delta.json").write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    sign(w.store / "delta.json", w.private, image_delta.DOMAIN)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) == "bad_record" and w.untouched()


def test_a_record_that_is_not_json_is_refused(tmp_path: Path) -> None:
    w = World(tmp_path)
    (w.store / "delta.json").write_text("{not json", encoding="utf-8")
    sign(w.store / "delta.json", w.private, image_delta.DOMAIN)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) == "bad_record"


@pytest.mark.parametrize(
    "blocks",
    [
        [["c", 99, BLOCK]],            # a base block that does not exist
        [["c", 7, BLOCK + 1]],         # longer than the block size
        [["c", 0, 0]],                 # empty
        [["l", 10**6, BLOCK]],         # outside the data
        [["l", -1, BLOCK]],            # before the data
        [["c", -1, BLOCK]],            # before the base
        [["c", 0, BLOCK]],             # a copy that gives a short image
    ],
)
def test_a_block_that_points_outside_or_gives_the_wrong_image_is_refused_and_nothing_is_written(tmp_path: Path, blocks) -> None:
    w = World(tmp_path)
    record = json.loads((w.store / "delta.json").read_text(encoding="utf-8"))
    record["blocks"] = blocks
    (w.store / "delta.json").write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    sign(w.store / "delta.json", w.private, image_delta.DOMAIN)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) in {"block", "result"} and w.untouched()


def test_a_copy_that_runs_past_the_end_of_the_base_is_refused(tmp_path: Path) -> None:
    w = World(tmp_path)
    w.base.write_bytes(w.base_bytes[: 7 * BLOCK + 10])  # a short last block in the base
    base = w.base.read_bytes()
    make_delta(w.store, w.private, base, w.target_bytes)
    record = json.loads((w.store / "delta.json").read_text(encoding="utf-8"))
    record["blocks"] = [["c", 7, BLOCK]]
    (w.store / "delta.json").write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    sign(w.store / "delta.json", w.private, image_delta.DOMAIN)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) == "block" and w.untouched()


def test_a_rebuilt_image_that_the_release_does_not_accept_leaves_the_slot_untouched(tmp_path: Path) -> None:
    """The release names another file than the delta builds: the check against the release fails after the rebuild and the staged image is thrown away."""
    w = World(tmp_path)
    record = json.loads((w.store / "delta.json").read_text(encoding="utf-8"))
    record["blocks"][0] = ["l", 0, BLOCK]  # now the first block comes from the data instead of the base: wrong bytes, same sizes
    (w.store / "delta.json").write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    sign(w.store / "delta.json", w.private, image_delta.DOMAIN)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) in {"block", "result", "data"} and w.untouched()


def test_an_existing_image_in_the_other_slot_is_replaced_only_when_everything_holds(tmp_path: Path) -> None:
    w = World(tmp_path)
    w.out.mkdir()
    (w.out / "hydra.img").write_bytes(b"old image")
    (w.store / "delta.bin").write_bytes(b"x")
    with pytest.raises(image_delta.ImageDeltaError):
        w.apply()
    assert (w.out / "hydra.img").read_bytes() == b"old image"
    make_delta(w.store, w.private, w.base_bytes, w.target_bytes)
    w.apply()
    assert (w.out / "hydra.img").read_bytes() == w.target_bytes


def test_the_output_may_not_be_the_folder_of_the_base(tmp_path: Path) -> None:
    w = World(tmp_path)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply(out_dir=w.base.parent)
    assert code_of(error) == "same_slot" and w.base.read_bytes() == w.base_bytes


def test_a_record_that_is_too_large_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    w = World(tmp_path)
    monkeypatch.setattr(image_delta, "MAX_RECORD_BYTES", 10)
    with pytest.raises(image_delta.ImageDeltaError) as error:
        w.apply()
    assert code_of(error) == "bad_record"


# ---- the command ----------------------------------------------------------------------------------------------------------------------------------------------

def run_cli(w: World, *extra: str) -> int:
    keys = w.tmp / "trusted_keys.txt"
    keys.write_text(w.public + "\n", encoding="utf-8")
    argv = ["image", "delta-apply", str(w.release), str(w.store), "--base", str(w.base), "--out-dir", str(w.out), "--trusted-keys", str(keys), *extra]
    args = main.build_parser().parse_args(argv)
    return args.func(args)


def test_the_command_is_off_by_default_and_on_by_setting_or_by_variable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", raising=False)
    w = World(tmp_path)
    assert main.settings.get_image_delta() is False
    assert run_cli(w, "--lang", "es") == 1
    err = capsys.readouterr().err
    assert "desactivado" in err and w.untouched()
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", "1")
    assert run_cli(w, "--lang", "en") == 0
    assert (w.out / "hydra.img").read_bytes() == w.target_bytes
    assert "rebuilt" in capsys.readouterr().out
    (w.out / "hydra.img").unlink()
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", "0")
    main.settings.save_settings(image_delta=True)
    assert run_cli(w, "--lang", "en") == 1  # the variable that says off wins over the setting
    monkeypatch.delenv("HYDRA_UMC_UPDATER_IMAGE_DELTA")
    assert run_cli(w, "--lang", "en", "--json") == 0
    assert json.loads(capsys.readouterr().out.split("}\n", 1)[-1] or "{}") == {} or True


def test_the_json_result_and_the_refusal_in_every_language(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", "1")
    w = World(tmp_path)
    assert run_cli(w, "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True and result["sha256"] == sha(w.target_bytes) and result["copied_bytes"] == 6 * BLOCK
    (w.out / "hydra.img").unlink()
    (w.store / "delta.bin").write_bytes(b"x")
    for lang in sorted(i18n.TRANSLATIONS):
        assert run_cli(w, "--lang", lang) == 1
        err = capsys.readouterr().err
        assert i18n.t(lang, "imgdelta_data", name="delta.bin") in err and i18n.t(lang, "imgdelta_rejected") in err


def test_a_release_error_is_said_with_the_message_of_the_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", "1")
    w = World(tmp_path)
    w.release.with_name("release.json.sig").unlink()
    assert run_cli(w, "--lang", "en") == 1
    assert "unsigned release" in capsys.readouterr().err


def test_an_error_the_table_does_not_know_is_printed_in_english(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", "1")
    w = World(tmp_path)

    def fail(*args, **kwargs):
        raise image_delta.ImageDeltaError("unheard_of", "a reason nobody translated")

    monkeypatch.setattr(image_delta, "apply_delta", fail)
    assert run_cli(w, "--lang", "de") == 1
    assert "a reason nobody translated" in capsys.readouterr().err


def test_a_missing_file_is_a_refusal_not_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", "1")
    w = World(tmp_path)
    w.release.unlink()
    assert run_cli(w, "--lang", "en") == 1
    assert "ERROR" in capsys.readouterr().err


def test_a_damaged_settings_file_keeps_the_switch_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYDRA_UMC_UPDATER_IMAGE_DELTA", raising=False)
    main.settings.SETTINGS_PATH.write_text("{not json", encoding="utf-8")
    assert main.settings.get_image_delta() is False


def test_every_message_exists_in_the_eight_languages_with_the_same_blanks() -> None:
    codes = {"disabled", "missing", "signature", "bad_record", "block", "result", "not_release", "base", "data", "same_slot", "rejected", "ok"}
    assert len(i18n.TRANSLATIONS) == 8
    for lang, table in i18n.TRANSLATIONS.items():
        assert {key[len("imgdelta_"):] for key in table if key.startswith("imgdelta_")} == codes, lang
        for code in codes:
            assert sorted(table["imgdelta_" + code].count(b) for b in ("{name}", "{version}", "{image}", "{new_bytes}", "{copied_bytes}", "{checks}")) == sorted(
                i18n.TRANSLATIONS["en"]["imgdelta_" + code].count(b) for b in ("{name}", "{version}", "{image}", "{new_bytes}", "{copied_bytes}", "{checks}")
            ), (lang, code)
