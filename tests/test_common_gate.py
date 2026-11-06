# =============================================================================
# Updater - tests/test_common_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What a project asks of the shared contracts (`min_common`) is read as a notice, never as a hold; and the reader is the same file in every updater.

The digest below is the one of the shared file `common_gate.py`. If the digest test fails because the file was edited, apply the same change to the copies in the other
updaters and put the new digest in the test of each."""
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = next(path.name for path in (ROOT / "src").iterdir() if (path / "common_gate.py").is_file())
SHARED_DIGEST = "413fcc7df8e8af8e0901619d0b45f3cbc37ddbdd57e7a017a5d058f9723ea1b1"
SIBLINGS = (
    ("HYDRA-UMC-UPDATER", "hydra_umc_updater"),
    ("URTC-UPDATER", "urtc_updater"),
    ("ARMOR-UPDATER", "armor_updater"),
)

gate = importlib.import_module(f"{PACKAGE}.common_gate")
settings = importlib.import_module(f"{PACKAGE}.settings")
main = importlib.import_module(f"{PACKAGE}.main")
core = importlib.import_module(f"{PACKAGE}.updater_core")
COPY = ROOT / "src" / PACKAGE / "common_gate.py"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_the_shared_gate_file_is_not_edited_in_one_place_only():
    assert _digest(COPY) == SHARED_DIGEST, "common_gate.py differs from the shared file: change every copy and the digest in every test"


@pytest.mark.parametrize("repo,package", SIBLINGS, ids=[name for name, _ in SIBLINGS])
def test_the_copies_next_to_this_repository_are_the_same_file(repo, package):
    other = ROOT.parent / repo / "src" / package / "common_gate.py"
    if not other.is_file():
        pytest.skip(f"{repo} is not next to this repository")
    assert _digest(other) == _digest(COPY), f"the copy in {repo} differs"


def test_the_mode_is_warn_by_default_and_a_typo_never_turns_it_off():
    assert gate.DEFAULT_MODE == "warn"
    assert gate.parse_mode(None) == gate.parse_mode("") == gate.parse_mode("wran") == gate.parse_mode(3) == "warn"
    assert gate.parse_mode(" OFF ") == "off"
    assert gate.parse_mode("Warn") == "warn"


def test_a_project_that_asks_for_a_newer_version_gets_a_notice():
    found = gate.notices_for([("P", "0.8.2.0")], "0.8.1.9")
    assert [(n.project, n.required, n.installed, n.status) for n in found] == [("P", "0.8.2.0", "0.8.1.9", "below")]
    assert "P asks for X 0.8.2.0 or newer" in gate.describe(found[0], "X")


def test_the_fourth_number_counts_and_a_missing_one_is_zero():
    assert gate.notices_for([("P", "0.8.0.1")], "0.8.0") != []
    assert gate.notices_for([("P", "0.8.0")], "0.8.0.0") == []
    assert gate.notices_for([("P", "0.9.0")], "0.10.0") == []
    assert gate.notices_for([("P", "0.8.1")], "0.8.1.3") == []


def test_nothing_is_said_when_nothing_is_asked_or_the_value_is_not_a_version():
    assert gate.notices_for([("P", None), ("Q", ""), ("R", "later"), ("S", "1.2")], "0.1.0") == []
    assert gate.notices_for([("P", "9.9.9")], "0.1.0", "off") == []


def test_an_unknown_installed_version_is_said_as_unknown_not_as_below():
    found = gate.notices_for([("P", "0.2.0")], None)
    assert found[0].status == "unknown" and found[0].installed is None
    assert gate.notices_for([("P", "0.2.0")], "garbage")[0].status == "unknown"
    assert gate.notices_for([("P", None)], None) == []


def _row(name, version=None, min_common=None, installed=True):
    return SimpleNamespace(installed=installed, version=version, entry=SimpleNamespace(name=name, min_common=min_common))


def test_the_status_reads_the_installed_version_of_the_shared_repository(monkeypatch):
    monkeypatch.delenv(core.PROFILE.env_name("MIN_COMMON") if hasattr(core, "PROFILE") else core.HYDRA_PROFILE.env_name("MIN_COMMON"), raising=False)
    monkeypatch.setattr(settings, "load_settings", lambda: {})
    rows = [_row(core.COMMON_REPO, "0.3.0"), _row("A", "1.0.0", "0.4.0"), _row("B", "1.0.0", "0.3.0"), _row("C", "1.0.0")]
    found = main._common_notices(rows)
    assert [(n.project, n.status) for n in found] == [("A", "below")]
    # not installed: whoever asks for a minimum gets an unknown notice
    rows[0] = _row(core.COMMON_REPO, None, installed=False)
    assert [(n.project, n.status) for n in main._common_notices(rows)] == [("A", "unknown"), ("B", "unknown")]


def test_the_switch_comes_from_the_environment_then_the_saved_setting(monkeypatch):
    profile = core.PROFILE if hasattr(core, "PROFILE") else core.HYDRA_PROFILE
    name = profile.env_name("MIN_COMMON")
    monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "load_settings", lambda: {})
    assert settings.min_common_mode() == "warn"
    monkeypatch.setattr(settings, "load_settings", lambda: {"min_common_check": "off"})
    assert settings.min_common_mode() == "off"
    monkeypatch.setenv(name, "warn")
    assert settings.min_common_mode() == "warn"
    monkeypatch.setenv(name, "off")
    monkeypatch.setattr(settings, "load_settings", lambda: {})
    assert settings.min_common_mode() == "off"
    assert main._common_notices([_row("A", "1.0.0", "9.9.9")]) == []
