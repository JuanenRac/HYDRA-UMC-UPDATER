# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_model_bundle_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
# ruff: noqa: F811
"""Edges of the signed bundle of models that the first tests leave out: a member that is damaged inside the archive, a size that is not the one announced,
a folder of models that leads outside of itself, a disk that fails while the files are put in place, and an installed registry that cannot be read. The
keys are made by the test; nothing is installed outside the test folder."""
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import pytest

from test_model_bundle import HEF1, V1, bundle, entry, key_file, make_zip, node, on, signed_members, sha  # noqa: F401  (fixtures are used by name)

from hydra_umc_updater import model_bundle  # noqa: E402
from hydra_umc_updater.package_release import PackageError  # noqa: E402


def stored_zip(path: Path, members: dict[str, bytes]) -> Path:
    import json

    listing = {name: sha(data) for name, data in sorted(members.items())}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("bundle.json", json.dumps({"format": 1, "files": listing}))
        for name, data in sorted(members.items()):
            archive.writestr(name, data)
    return path


def refused(code: str, *args, **kwargs) -> PackageError:
    with pytest.raises(PackageError) as caught:
        model_bundle.install_bundle(*args, **kwargs)
    assert caught.value.code == code, caught.value
    return caught.value


def test_a_member_whose_bytes_were_damaged_in_the_archive_is_unreadable_and_nothing_is_written(tmp_path, key_file, node, on):
    registry, models = node
    members = signed_members(V1, {"det-1.0.0.hef": HEF1})
    path = stored_zip(tmp_path / "damaged.zip", members)
    raw = bytearray(path.read_bytes())
    at = bytes(raw).index(HEF1)
    raw[at] ^= 0x01
    path.write_bytes(bytes(raw))
    refused("models_unreadable", path, registry, models, key_file)
    assert not registry.exists() and not list(models.iterdir())


def test_a_member_that_is_not_the_size_the_archive_announces_is_refused(tmp_path, key_file, node, on, monkeypatch):
    registry, models = node
    path = bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1})
    monkeypatch.setattr(zipfile.ZipFile, "open", lambda self, info, *a, **k: io.BytesIO(b"short"))
    refused("models_hash_bad", path, registry, models, key_file)
    assert not registry.exists()


def test_a_disk_that_fails_while_the_files_are_put_in_place_is_reported_as_an_install_failure(tmp_path, key_file, node, on, monkeypatch):
    registry, models = node

    def fails(destination, data):
        raise OSError("disk full")

    monkeypatch.setattr(model_bundle, "_replace", fails)
    error = refused("models_install_failed", bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
    assert "disk full" in str(error)


def test_an_installed_registry_that_cannot_be_read_stops_the_update(tmp_path, key_file, node, on, monkeypatch):
    registry, models = node
    model_bundle.install_bundle(bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}), registry, models, key_file)
    real = Path.read_bytes

    def unreadable(self):
        if self == registry:
            raise OSError("permission denied")
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    error = refused("models_registry_bad", bundle(tmp_path, V1, {"det-1.0.0.hef": HEF1}, name="again.zip"), registry, models, key_file)
    assert "permission denied" in str(error)


def test_two_entries_of_one_model_count_as_its_newest(tmp_path, key_file, node, on):
    registry, models = node
    older, newer = entry("det", "1.0.0", HEF1), entry("det", "1.2.0", b"newer")
    result = model_bundle.install_bundle(bundle(tmp_path, [older, newer], {"det-1.0.0.hef": HEF1, "det-1.2.0.hef": b"newer"}), registry, models, key_file)
    assert result.models == ("det 1.0.0", "det 1.2.0")
    # going back to the older one alone is a downgrade of the newest, whatever order the entries were listed in
    refused("models_downgrade", bundle(tmp_path, [older], {"det-1.0.0.hef": HEF1}, name="back.zip"), registry, models, key_file)


@pytest.mark.skipif(os.name == "nt", reason="a symbolic link needs a privilege on Windows")
def test_a_folder_of_models_that_leads_outside_of_itself_is_refused_before_any_write(tmp_path, key_file, node, on):
    registry, models = node
    outside = tmp_path / "outside"
    outside.mkdir()
    (models / "sub").symlink_to(outside, target_is_directory=True)
    sub = dict(entry("det", "1.0.0", HEF1), hef_path="sub/det-1.0.0.hef")
    refused("models_member_bad", bundle(tmp_path, [sub], {"sub/det-1.0.0.hef": HEF1}), registry, models, key_file)
    assert not list(outside.iterdir()) and not registry.exists()
