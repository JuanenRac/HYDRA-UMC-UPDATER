# =============================================================================
# HYDRA-UMC-UPDATER - GitHub version lookup: github_client.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Fetches each project's universal manifest directly from GitHub raw content.
#
# IMPORTANT:
#
# This does NOT use GitHub Releases or tags.
#
# The ecosystem's versioning convention stores the public project version in
# hydra-umc.project.json. Builds must keep their native package/firmware
# version synchronized with that manifest; local validation catches drift.
#
# Architecture:
#
#   registry.py
#        |
#        v
#   github_raw_url()
#        |
#        v
#   GitHub raw content
#        |
#        v
#   parse_manifest()
#
# stdlib-only:
#
#   urllib
#   concurrent.futures
#   dataclasses
#
# No requests dependency is required.
# =============================================================================

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass

from .project_manifest import (
    ECOSYSTEM_ID,
    MANIFEST_FILE,
    ManifestValidationError,
    ProjectManifest,
    parse_manifest,
)
from .registry import (
    ProjectEntry,
    entry_from_manifest,
    github_native_version_url,
    github_raw_url,
)
from .version_parse import Version, parse_version


# ---------------------------------------------------------------------------
# Network configuration
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT_S = 10

# GitHub is being queried for small text files only.
#
# Keeping this moderate avoids turning a simple version checker into a
# high-concurrency crawler.
MAX_CONCURRENT_REQUESTS = 8

USER_AGENT = "HYDRA-UMC-UPDATER"


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class RemoteStatus:
    """
    Result of looking up one project's remote version.

    version:
        Parsed semantic version, or None when the lookup failed.

    error:
        Human-readable reason for failure, or None when successful.

    http_status:
        HTTP status code when GitHub returned an HTTP error.

    url:
        Raw manifest URL that was queried. This is useful for verbose diagnostics.

    """

    entry: ProjectEntry

    version: Version | None

    error: str | None = None

    http_status: int | None = None

    url: str | None = None

    manifest: ProjectManifest | None = None


@dataclass(frozen=True)
class RemoteDiscovery:
    """Projects positively identified by their own GitHub manifest."""

    projects: tuple[RemoteStatus, ...]
    errors: tuple[str, ...]


def _fetch_discovered_manifest(owner: str, name: str, branch: str) -> RemoteStatus | None:
    """Return a project only when its own manifest opts into HYDRA-UMC."""
    url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{MANIFEST_FILE}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"{name}: manifest HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise RuntimeError(f"{name}: manifest lookup failed: {exc}") from exc

    try:
        manifest = parse_manifest(text, expected_name=name)
    except ManifestValidationError as exc:
        # A repository that exposes this exact manifest path is relevant to
        # the maintainer even when it is malformed; surface it in workflow
        # logs rather than silently treating it as a non-ecosystem project.
        raise RuntimeError(f"{name}: invalid manifest: {exc}") from exc

    if manifest.ecosystem != ECOSYSTEM_ID:
        return None
    major, minor, patch = (int(part) for part in manifest.version.split("."))
    return RemoteStatus(
        entry=entry_from_manifest(manifest),
        version=Version(major, minor, patch),
        url=url,
        manifest=manifest,
    )


def discover_remote_projects(
    owner: str = "JuanenRac",
    *,
    token: str | None = None,
) -> RemoteDiscovery:
    """Discover every public ecosystem repository from GitHub, no fixed list.

    GitHub's repository listing is only a candidate list. A repository joins
    the ecosystem only after its own root manifest validates and declares
    ``ecosystem: HYDRA-UMC``. A newly pushed repository therefore appears on
    the next dashboard or updater scan without an index.html edit.
    """
    resolved_token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    candidates: list[tuple[str, str]] = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{owner}/repos?type=owner&per_page=100&page={page}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"unable to list GitHub repositories for {owner}: {exc}") from exc
        if not isinstance(payload, list):
            raise RuntimeError(f"unexpected GitHub repository-list response for {owner}")
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                branch = item.get("default_branch")
                candidates.append((item["name"], branch if isinstance(branch, str) and branch else "main"))
        if len(payload) < 100:
            break
        page += 1

    discovered: list[RemoteStatus] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS, thread_name_prefix="hydra-discovery") as pool:
        futures = {pool.submit(_fetch_discovered_manifest, owner, name, branch): name for name, branch in candidates}
        for future in as_completed(futures):
            name = futures[future]
            try:
                status = future.result()
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            if status is not None:
                discovered.append(status)

    discovered.sort(key=lambda status: status.entry.name.casefold())
    return RemoteDiscovery(projects=tuple(discovered), errors=tuple(sorted(errors)))


# ---------------------------------------------------------------------------
# One project
# ---------------------------------------------------------------------------

def _fetch_one(
    entry: ProjectEntry,
) -> RemoteStatus:
    """
    Fetch and parse the version for one project.

    This function intentionally never raises ordinary network/HTTP errors
    to the caller. A single broken repository must not abort the complete
    ecosystem scan.
    """

    url = github_raw_url(entry)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/plain,*/*",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_S,
        ) as response:

            raw = response.read()

            text = raw.decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            # Compatibility path for a caller that already supplied a valid
            # local manifest but whose remote manifest has not yet been
            # published. No central project metadata is used here.
            native_url = github_native_version_url(entry)
            native_request = urllib.request.Request(
                native_url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*"},
                method="GET",
            )
            try:
                with urllib.request.urlopen(native_request, timeout=REQUEST_TIMEOUT_S) as response:
                    native_text = response.read().decode("utf-8", errors="replace")
                native_version = parse_version(native_text, entry.pattern)
                if native_version is not None:
                    return RemoteStatus(
                        entry=entry,
                        version=native_version,
                        error=None,
                        http_status=None,
                        url=native_url,
                    )
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, OSError):
                pass
        # Typical cases:
        #
        #   404 -> version file/repository/path disappeared
        #   403 -> rate limit or access restriction
        #   429 -> too many requests
        #   500+ -> GitHub/server problem
        #
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"HTTP {exc.code}",
            http_status=exc.code,
            url=url,
        )

    except urllib.error.URLError as exc:
        reason = getattr(
            exc,
            "reason",
            "unknown network error",
        )

        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"network error: {reason}",
            url=url,
        )

    except (TimeoutError, socket.timeout):
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"timed out after {REQUEST_TIMEOUT_S}s",
            url=url,
        )

    except OSError as exc:
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"OS/network error: {exc}",
            url=url,
        )

    except Exception as exc:
        # Last-resort protection:
        #
        # One unexpected parser/network implementation error should still
        # become an "unknown" project instead of killing all 44/45 lookups.
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"unexpected error: {type(exc).__name__}: {exc}",
            url=url,
        )

    # -----------------------------------------------------------------------
    # Manifest and version parsing
    # -----------------------------------------------------------------------

    try:
        manifest = parse_manifest(text, expected_name=entry.name)
        major, minor, patch = (int(part) for part in manifest.version.split("."))
        version = Version(major, minor, patch)
    except ManifestValidationError as exc:
        return RemoteStatus(
            entry=entry,
            version=None,
            error=f"invalid project manifest: {exc}",
            url=url,
        )

    return RemoteStatus(
        entry=entry,
        version=version,
        error=None,
        http_status=None,
        url=url,
        manifest=manifest,
    )


# ---------------------------------------------------------------------------
# All projects
# ---------------------------------------------------------------------------

def fetch_all(
    entries: list[ProjectEntry],
    progress=None,
) -> dict[str, RemoteStatus]:
    """
    Fetch the latest GitHub version for every given entry.

    Parameters
    ----------
    entries:
        Projects to query.

        Discovered local or remote project entries. The caller must supply
        them; this module deliberately has no fixed project catalogue.

    progress:
        Optional callback:

            progress(done, total)

        It is called after each individual request completes.

    Returns
    -------
    dict[str, RemoteStatus]

        Dictionary keyed by project name.

    Notes
    -----
    Requests are performed concurrently, but the concurrency is intentionally
    limited to MAX_CONCURRENT_REQUESTS.

    Results are inserted as soon as each request completes. Therefore the
    dictionary's insertion order is completion order. Consumers can apply
    their own family/name ordering after discovery.
    """

    targets = entries

    results: dict[str, RemoteStatus] = {}

    total = len(targets)
    done = 0

    if total == 0:
        return results

    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENT_REQUESTS,
        thread_name_prefix="hydra-github",
    ) as pool:

        futures = {
            pool.submit(
                _fetch_one,
                entry,
            ): entry
            for entry in targets
        }

        for future in as_completed(futures):
            entry = futures[future]

            try:
                status = future.result()

            except Exception as exc:
                # This should normally never happen because _fetch_one already
                # converts expected failures into RemoteStatus. It is kept as
                # a final isolation boundary anyway.
                status = RemoteStatus(
                    entry=entry,
                    version=None,
                    error=(
                        "worker failure: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    url=github_raw_url(entry),
                )

            results[
                status.entry.name
            ] = status

            done += 1

            if progress is not None:
                progress(
                    done,
                    total,
                )

    return results
