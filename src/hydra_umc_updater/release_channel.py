# =============================================================================
# HYDRA-UMC-UPDATER - Latest published release of a repository: release_channel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Finds the release of a repository that the updater installs: the latest STABLE one, never the head of the branch.

The stable channel takes the newest published release that is neither a draft nor a pre-release. The optional "pruebas" channel (off
unless the settings name it) also accepts pre-releases. The tag of the chosen release is resolved to the commit it points at, so the
caller can install exactly that commit.

Fail closed: no network, an answer that is not what the GitHub API sends, no release in the channel, or a tag that cannot be resolved
raise `ReleaseError` with a reason; the caller installs nothing. There is no fallback to the head of the branch.

The only network access is `fetch_json(url)`, which tests replace with a function that serves made-up API answers.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import github_client
from .registry import GITHUB_OWNER

#: `v0.8.1.0`, `0.8.1`, and (only on the "pruebas" channel) `v0.8.1.0-rc1`.
_TAG = re.compile(r"^v?(\d+\.\d+\.\d+(?:\.\d+)?)(-[0-9A-Za-z.]+)?$")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
RELEASES_PER_PAGE = 30
CHANNELS = ("stable", "pruebas")

Fetcher = Callable[[str], Any]


class ReleaseError(RuntimeError):
    """No release can be chosen. `code` names the reason (a key of the translations: `rel_<code>`), `params` fill its blanks."""

    def __init__(self, code: str, english: str, **params: object) -> None:
        super().__init__(english)
        self.code = code
        self.params = params


@dataclass(frozen=True)
class ReleaseInfo:
    repo: str
    tag: str
    version: str
    prerelease: bool
    plain: bool  # the tag is a plain version (no suffix): it must equal the version of the manifest at that commit
    commit: str
    assets: dict[str, str] = field(default_factory=dict)  # asset name -> download address


def fetch_json(url: str) -> Any:
    """GET a GitHub API address and parse the JSON. A `GITHUB_TOKEN` in the environment is sent to raise the rate limit."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": github_client.USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    raw = github_client._urlopen_with_retries(request, timeout=github_client.REQUEST_TIMEOUT_S)
    return json.loads(raw.decode("utf-8"))


def _version_key(version: str) -> tuple[int, ...]:
    parts = [int(part) for part in version.split(".")]
    return tuple(parts + [0] * (4 - len(parts)))


def _candidates(releases: Any, channel: str) -> list[tuple[tuple[int, ...], dict[str, Any], str, bool]]:
    if not isinstance(releases, list):
        raise ReleaseError("bad_answer", "the release list is not a list")
    found = []
    for item in releases:
        if not isinstance(item, dict) or item.get("draft") is True:
            continue
        pre = item.get("prerelease") is True
        if pre and channel != "pruebas":
            continue
        tag = item.get("tag_name")
        match = _TAG.match(tag) if isinstance(tag, str) else None
        if match is None:
            continue
        plain = match.group(2) is None
        if not plain and not pre:
            # a suffix on a tag that is not marked as a pre-release is not a version the stable channel can order: skip it
            continue
        # a plain version ranks above its own release candidates
        found.append(((*_version_key(match.group(1)), 1 if plain else 0), item, match.group(1), plain))
    return found


def _commit_of_tag(base: str, tag: str, fetch: Fetcher) -> str:
    ref = fetch(f"{base}/git/ref/tags/{urllib.parse.quote(tag, safe='')}")
    obj = ref.get("object") if isinstance(ref, dict) else None
    if not isinstance(obj, dict) or not isinstance(obj.get("sha"), str):
        raise ReleaseError("bad_answer", f"the tag {tag} has no usable reference")
    for _ in range(3):  # a tag object may point at another tag object
        if obj.get("type") == "commit" and _SHA1.match(obj["sha"]):
            return obj["sha"]
        if obj.get("type") != "tag":
            break
        tag_object = fetch(f"{base}/git/tags/{obj['sha']}")
        obj = tag_object.get("object") if isinstance(tag_object, dict) else None
        if not isinstance(obj, dict) or not isinstance(obj.get("sha"), str):
            break
    raise ReleaseError("bad_answer", f"the tag {tag} does not lead to a commit")


def resolve_latest(repo: str, channel: str = "stable", *, fetch: Fetcher | None = None, owner: str = GITHUB_OWNER) -> ReleaseInfo:
    """The newest release of `repo` in `channel`, with the commit its tag points at. Raises ReleaseError; never returns a head."""
    fetch = fetch or fetch_json  # looked up now, so a test can replace fetch_json
    if channel not in CHANNELS:
        raise ReleaseError("bad_answer", f"unknown channel {channel!r}")
    if not _NAME.match(repo) or not _NAME.match(owner):
        raise ReleaseError("bad_answer", f"{repo!r} is not a repository name")
    base = f"{github_client.GITHUB_API_BASE}/repos/{owner}/{repo}"
    try:
        releases = fetch(f"{base}/releases?per_page={RELEASES_PER_PAGE}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise ReleaseError("unreachable", f"the releases of {repo} cannot be read: {error}", repo=repo) from error
    candidates = _candidates(releases, channel)
    if not candidates:
        raise ReleaseError("none", f"{repo} has no published {channel} release", repo=repo, channel=channel)
    _, item, version, plain = max(candidates, key=lambda c: c[0])
    tag = item["tag_name"]
    try:
        commit = _commit_of_tag(base, tag, fetch)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        raise ReleaseError("unreachable", f"the tag {tag} of {repo} cannot be resolved: {error}", repo=repo) from error
    assets: dict[str, str] = {}
    for asset in item.get("assets") or []:
        if isinstance(asset, dict) and isinstance(asset.get("name"), str) and isinstance(asset.get("browser_download_url"), str):
            assets[asset["name"]] = asset["browser_download_url"]
    return ReleaseInfo(repo, tag, version, item.get("prerelease") is True, plain, commit, assets)
