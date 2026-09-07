# =============================================================================
# HYDRA-UMC-UPDATER - Shared version-string extraction: version_parse.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# One parsing implementation, used identically by detect.py (a local file
# read) and github_client.py (a raw-content HTTP fetch). The repository
# manifest's native_version.pattern is the only per-project input, so
# whichever source the raw text came from, it's interpreted the exact same
# way here. Keeping this in one place is deliberate: two independent regex
# implementations (one for local files, one for GitHub responses) could
# silently drift and report a false "up to date"/"outdated" for one source
# but not the other - a bug that would be very easy to ship and very
# confusing to debug.
# =============================================================================
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "Version") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "Version") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)


def parse_version(text: str, pattern) -> Version | None:
    """Extract a Version using a manifest-declared pattern: one 3-group
    regex, or a dict of 3
    separate 1-group regexes keyed major/minor/patch). Returns None rather
    than raising on no match - a project whose version file moved, got
    renamed, or simply doesn't exist yet locally is a normal, expected
    state for detect.py/github_client.py to report as "unknown", not a
    crash."""
    if isinstance(pattern, dict):
        parts: dict[str, int] = {}
        for key in ("major", "minor", "patch"):
            match = re.search(pattern[key], text, re.MULTILINE)
            if not match:
                return None
            parts[key] = int(match.group(1))
        return Version(parts["major"], parts["minor"], parts["patch"])

    match = re.search(pattern, text, re.MULTILINE)
    if not match or len(match.groups()) < 3:
        return None
    return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))
