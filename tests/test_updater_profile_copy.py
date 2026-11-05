# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_updater_profile_copy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""`updater_profile.py` is the same file in every updater: nobody edits it in one place only.

The digest below is the one of the shared file. If this test fails because the file was edited, apply the same change to the copies in the other updaters
and put the new digest in the test of each. When the other updaters are next to this repository their copies are compared byte for byte too."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

SHARED_DIGEST = "24e4b1aa3f05e2fc8c40bc28fdf88b3e69eb634a82437bd3fbba066d869a9fa4"
ROOT = Path(__file__).resolve().parent.parent
COPY = ROOT / "src" / "hydra_umc_updater" / "updater_profile.py"
SIBLINGS = (
    ("HYDRA-UMC-UPDATER", "hydra_umc_updater"),
    ("URTC-UPDATER", "urtc_updater"),
    ("ARMOR-UPDATER", "armor_updater"),
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_the_shared_profile_file_is_not_edited_in_one_place_only():
    assert _digest(COPY) == SHARED_DIGEST, "updater_profile.py differs from the shared file: change every copy and the digest in every test"


@pytest.mark.parametrize("repo,package", SIBLINGS, ids=[name for name, _ in SIBLINGS])
def test_the_copies_next_to_this_repository_are_the_same_file(repo, package):
    other = ROOT.parent / repo / "src" / package / "updater_profile.py"
    if not other.is_file():
        pytest.skip(f"{repo} is not next to this repository")
    assert _digest(other) == _digest(COPY), f"the copy in {repo} differs"
