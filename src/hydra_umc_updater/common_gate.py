# =============================================================================
# Common gate - what a project asks of the shared contracts, read as a notice
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The part of the common core that reads `min_common` and compares it with the installed shared contracts.

This file is copied, byte for byte, into the HYDRA-UMC, URTC and A.R.M.O.R. updaters (and into any other updater that adopts the core). It imports
nothing from the package it lives in; a test in each updater pins the digest of the file and compares it with the copies next to it when they are present.
To change it, change all the copies in one go and update the digest in the tests.

A project may say, with the optional `min_common` of its manifest, the oldest version of the shared contracts repository it works with. This module
turns that into a notice when the installed contracts are older. It only warns: nothing is held back, nothing is refused, and a value that is not a
version says nothing. The mode is `warn` (the default) or `off`; anything else is read as the default, so a typo never silences the notice by accident."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
MODES: tuple[str, ...] = ("warn", "off")
DEFAULT_MODE = "warn"


@dataclass(frozen=True)
class CommonNotice:
    """One project that asks for a newer shared contracts repository than the one installed (or than anything known)."""

    project: str
    required: str
    #: the installed version of the shared contracts, None when it is not installed or its version could not be read
    installed: str | None

    @property
    def status(self) -> str:
        return "unknown" if self.installed is None else "below"

    def as_dict(self) -> dict[str, str | None]:
        return {"project": self.project, "required": self.required, "installed": self.installed, "status": self.status}


def parse_mode(value: object) -> str:
    """`warn` or `off`; anything else (absent, misspelled, not a text) is the default."""
    text = value.strip().lower() if isinstance(value, str) else ""
    return text if text in MODES else DEFAULT_MODE


def version_key(text: str) -> tuple[int, int, int, int] | None:
    """The numbers of a version (three or four, a missing fourth is 0); None when the text is not a version."""
    if not isinstance(text, str) or not VERSION_RE.fullmatch(text):
        return None
    numbers = [int(part) for part in text.split(".")]
    return (numbers[0], numbers[1], numbers[2], numbers[3] if len(numbers) == 4 else 0)


def notices_for(rows: Iterable[tuple[str, str | None]], installed: str | None, mode: str = DEFAULT_MODE) -> list[CommonNotice]:
    """The notices for `rows` (project name, its `min_common`) against the installed shared contracts version.

    Nothing when the mode is off, when a project asks for nothing or for something that is not a version, or when the installed version is at least
    what it asks. When the installed version is missing or unreadable, a project that asks for a minimum gets an `unknown` notice."""
    if parse_mode(mode) == "off":
        return []
    have = version_key(installed) if installed else None
    found: list[CommonNotice] = []
    for project, required in rows:
        need = version_key(required) if required else None
        if need is None:
            continue
        if have is None:
            found.append(CommonNotice(project, required, None))
        elif have < need:
            found.append(CommonNotice(project, required, installed))
    return found


def describe(notice: CommonNotice, common_name: str) -> str:
    """The sentence for one notice, naming the shared contracts repository of the family."""
    if notice.installed is None:
        return f"{notice.project} asks for {common_name} {notice.required} or newer, and the installed version of {common_name} is not known"
    return f"{notice.project} asks for {common_name} {notice.required} or newer, and {notice.installed} is installed"
