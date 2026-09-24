# =============================================================================
# HYDRA-UMC-UPDATER - Three- and four-part version handling
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import pytest

from hydra_umc_updater.project_manifest import VERSION_RE
from hydra_umc_updater.version_parse import Version, parse_version

BACKSLASH = chr(92)
THREE_OR_FOUR = BACKSLASH.join(["(", "d+)", ".(", "d+)", ".(", "d+)(?:", ".(", "d+))?"])
FOUR_PATTERN = '^version = "' + THREE_OR_FOUR + '"'


def test_from_string_reads_three_and_four_components():
    assert str(Version.from_string("0.7.9")) == "0.7.9"
    assert str(Version.from_string("0.8.0.0")) == "0.8.0.0"
    assert Version.from_string("0.8.0.3").build == 3


@pytest.mark.parametrize("bad", ["", "1", "1.2", "1.2.3.4.5", "a.b.c"])
def test_from_string_rejects_anything_else(bad):
    with pytest.raises(ValueError):
        Version.from_string(bad)


def test_ordering_follows_the_fourth_component():
    assert Version.from_string("0.7.9") < Version.from_string("0.8.0.0")
    assert Version.from_string("0.8.0.0") < Version.from_string("0.8.0.1")
    assert Version.from_string("0.8.0.9") < Version.from_string("0.8.1.0")
    assert Version.from_string("0.8.1.0") <= Version.from_string("0.8.1.0")


def test_a_missing_fourth_component_equals_zero_but_prints_as_written():
    assert Version.from_string("0.8.0") == Version.from_string("0.8.0.0")
    assert str(Version.from_string("0.8.0")) == "0.8.0"


def test_parse_version_reads_the_optional_fourth_group():
    assert str(parse_version('version = "0.8.0.4"', FOUR_PATTERN.replace("^", "^", 1))) == "0.8.0.4"
    assert str(parse_version('version = "0.7.9"', FOUR_PATTERN)) == "0.7.9"


def test_the_manifest_version_pattern_accepts_both_shapes():
    assert VERSION_RE.fullmatch("0.7.9")
    assert VERSION_RE.fullmatch("0.8.0.0")
    assert not VERSION_RE.fullmatch("0.8")
    assert not VERSION_RE.fullmatch("0.8.0.0.0")
