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
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Version:
    """MAJOR.MINOR.PATCH, with an optional fourth BUILD component.

    A missing fourth component compares as 0 (0.8.0 == 0.8.0.0) but is printed
    as it was written, so a manifest that says 0.8.0.0 is shown as 0.8.0.0.
    """

    major: int
    minor: int
    patch: int
    build: int = 0
    has_build: bool = field(default=False, compare=False)

    @classmethod
    def from_string(cls, text: str) -> "Version":
        parts = [int(part) for part in text.split(".")]
        if len(parts) == 3:
            return cls(parts[0], parts[1], parts[2])
        if len(parts) == 4:
            return cls(parts[0], parts[1], parts[2], parts[3], has_build=True)
        raise ValueError(f"not a MAJOR.MINOR.PATCH[.BUILD] version: {text!r}")

    def _key(self) -> tuple[int, int, int, int]:
        return (self.major, self.minor, self.patch, self.build)

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}.{self.build}" if self.has_build else base

    def __lt__(self, other: "Version") -> bool:
        return self._key() < other._key()

    def __le__(self, other: "Version") -> bool:
        return self._key() <= other._key()


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
        if "build" in pattern and (parts["major"], parts["minor"], parts["patch"]) >= (0, 8, 0):
            build = re.search(pattern["build"], text, re.MULTILINE)
            if build:
                return Version(parts["major"], parts["minor"], parts["patch"], int(build.group(1)), has_build=True)
        return Version(parts["major"], parts["minor"], parts["patch"])

    match = re.search(pattern, text, re.MULTILINE)
    if not match or len(match.groups()) < 3:
        return None
    if len(match.groups()) >= 4 and match.group(4) is not None:
        return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), has_build=True)
    return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))
