# =============================================================================
# HYDRA-UMC-UPDATER - GitHub client tests: malformed catalog + retries
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real fixture-server tests for the remote catalog discovery path, plus
direct unit tests for the new transient-network retry/backoff logic.

Malformed-catalog and mixed-validity scans run against a real local
`http.server.HTTPServer` (started in a background thread) rather than a
mocked transport - the same real-request/real-response philosophy this
ecosystem's Go projects apply via `net/http/httptest`. The low-level
retry/backoff behavior of `_urlopen_with_retries` is tested with an
injectable fake opener/sleep instead, since it needs to observe exact
attempt counts and backoff delays without real network flakiness or real
wall-clock waits.
"""
from __future__ import annotations

import email.message
import http.server
import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from hydra_umc_updater import github_client
from hydra_umc_updater.github_client import (
    _fetch_one,
    _retry_after_seconds,
    _urlopen_with_retries,
    describe_http_error,
    discover_remote_projects,
)
from hydra_umc_updater.registry import ProjectEntry


def _http_error(code: int, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    """Builds a real urllib.error.HTTPError carrying real response
    headers - `exc.headers` is an `email.message.Message`-like object in
    real usage, same shape urllib itself constructs it with."""
    message = email.message.Message()
    for key, value in (headers or {}).items():
        message[key] = value
    return urllib.error.HTTPError("http://example.invalid/manifest", code, "error", message, None)


def valid_manifest(name: str, version: str = "1.2.3") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "ecosystem": "HYDRA-UMC",
        "name": name,
        "version": version,
        "role": "service",
        "stack": "python",
        "technologies": ["Python"],
        "deployment_target": "cm5",
        "maturity": "functional",
        "family": "Example family",
        "parent": None,
        "native_version": {
            "file": "pyproject.toml",
            "pattern": "^version\\s*=\\s*\"(\\d+)\\.(\\d+)\\.(\\d+)\"",
        },
        "build": "python -m build",
        "notes": "Fixture manifest.",
    }


class _FixtureHandler(http.server.BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, bytes]] = {}

    def log_message(self, format, *args):
        pass  # keep the real test server quiet

    def do_GET(self) -> None:
        entry = self.routes.get(self.path)
        if entry is None:
            self.send_response(404)
            self.end_headers()
            return
        status, body = entry
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def fixture_server(routes: dict[str, tuple[int, bytes]]):
    handler_cls = type("_RoutedFixtureHandler", (_FixtureHandler,), {"routes": routes})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Malformed remote catalog fixtures
# ---------------------------------------------------------------------------


def test_discover_remote_projects_raises_clearly_on_malformed_repo_list_json(monkeypatch):
    with fixture_server(
        {"/users/JuanenRac/repos?type=owner&per_page=100&page=1": (200, b"{not valid json")}
    ) as base_url:
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base_url)
        with pytest.raises(RuntimeError, match="unable to list GitHub repositories"):
            discover_remote_projects()


def test_discover_remote_projects_raises_clearly_on_unexpected_top_level_shape(monkeypatch):
    with fixture_server(
        {"/users/JuanenRac/repos?type=owner&per_page=100&page=1": (200, b'{"not": "a list"}')}
    ) as base_url:
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base_url)
        with pytest.raises(RuntimeError, match="unexpected GitHub repository-list response"):
            discover_remote_projects()


def test_discover_remote_projects_isolates_one_malformed_manifest_from_the_rest(monkeypatch):
    repo_list = json.dumps(
        [
            {"name": "GoodProject", "default_branch": "main"},
            {"name": "BadProject", "default_branch": "main"},
            {"name": "NoManifestHere", "default_branch": "main"},
        ]
    ).encode()

    routes = {
        "/users/JuanenRac/repos?type=owner&per_page=100&page=1": (200, repo_list),
        "/JuanenRac/GoodProject/main/hydra-umc.project.json": (200, json.dumps(valid_manifest("GoodProject")).encode()),
        "/JuanenRac/BadProject/main/hydra-umc.project.json": (200, b"{not valid json"),
        # NoManifestHere deliberately has no route at all - the fixture
        # server's do_GET() answers with a real 404, exactly like a
        # repository that never published hydra-umc.project.json.
    }
    with fixture_server(routes) as base_url:
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base_url)
        monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base_url)
        discovery = discover_remote_projects()

    # The one real, valid, HYDRA-UMC manifest is discovered...
    assert [status.entry.name for status in discovery.projects] == ["GoodProject"]
    # ...the malformed one is isolated into `errors`, not silently dropped...
    assert len(discovery.errors) == 1
    assert "BadProject" in discovery.errors[0]
    # ...and a repo with no manifest at all is neither a project nor an
    # error - a real 404 there just means "not part of this ecosystem".
    assert not any("NoManifestHere" in error for error in discovery.errors)


# ---------------------------------------------------------------------------
# Retry/backoff for genuinely transient network failures
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._data


def test_urlopen_with_retries_recovers_after_transient_failures():
    attempts: list[int] = []
    sleeps: list[float] = []

    def opener(request, timeout):
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise urllib.error.URLError("connection refused")
        return _FakeResponse(b"payload")

    request = urllib.request.Request("http://example.invalid/manifest")
    result = _urlopen_with_retries(
        request, timeout=1, max_attempts=3, backoff_base_s=0.01, opener=opener, sleep=sleeps.append
    )

    assert result == b"payload"
    assert attempts == [1, 2, 3]
    assert sleeps == [0.01, 0.02]


def test_urlopen_with_retries_gives_up_after_max_attempts():
    attempts: list[int] = []

    def opener(request, timeout):
        attempts.append(len(attempts) + 1)
        raise urllib.error.URLError("connection refused")

    request = urllib.request.Request("http://example.invalid/manifest")
    with pytest.raises(urllib.error.URLError):
        _urlopen_with_retries(
            request, timeout=1, max_attempts=3, backoff_base_s=0.01, opener=opener, sleep=lambda _s: None
        )

    assert len(attempts) == 3


def test_urlopen_with_retries_never_retries_a_definitive_http_error():
    attempts: list[int] = []

    def opener(request, timeout):
        attempts.append(len(attempts) + 1)
        raise urllib.error.HTTPError(request.full_url, 404, "not found", None, None)

    request = urllib.request.Request("http://example.invalid/manifest")
    with pytest.raises(urllib.error.HTTPError):
        _urlopen_with_retries(request, timeout=1, opener=opener, sleep=lambda _s: None)

    assert len(attempts) == 1


def test_urlopen_with_retries_retries_a_secondary_rate_limit_then_succeeds():
    # Found in an ecosystem-wide software-improvements audit: GitHub's own
    # real secondary-rate-limit signal (403/429 + Retry-After) is short
    # and genuinely worth retrying within this same process, unlike the
    # hourly primary limit.
    attempts: list[int] = []
    sleeps: list[float] = []

    def opener(request, timeout):
        attempts.append(len(attempts) + 1)
        if len(attempts) < 2:
            raise _http_error(403, {"Retry-After": "1.5"})
        return _FakeResponse(b"payload")

    request = urllib.request.Request("http://example.invalid/manifest")
    result = _urlopen_with_retries(
        request, timeout=1, max_attempts=3, backoff_base_s=0.01, opener=opener, sleep=sleeps.append
    )

    assert result == b"payload"
    assert attempts == [1, 2]
    assert sleeps == [1.5]


def test_urlopen_with_retries_never_retries_a_rate_limit_without_retry_after():
    # The hourly PRIMARY rate limit (X-RateLimit-Reset, no Retry-After) can
    # be tens of minutes away - never worth blocking a foreground run for.
    attempts: list[int] = []

    def opener(request, timeout):
        attempts.append(len(attempts) + 1)
        raise _http_error(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700000000"})

    request = urllib.request.Request("http://example.invalid/manifest")
    with pytest.raises(urllib.error.HTTPError):
        _urlopen_with_retries(request, timeout=1, opener=opener, sleep=lambda _s: None)

    assert len(attempts) == 1


def test_retry_after_seconds_reads_a_real_header():
    assert _retry_after_seconds(_http_error(403, {"Retry-After": "3"})) == 3.0
    assert _retry_after_seconds(_http_error(429, {"Retry-After": "0.5"})) == 0.5


def test_retry_after_seconds_is_none_without_the_header_or_wrong_code():
    assert _retry_after_seconds(_http_error(403)) is None
    assert _retry_after_seconds(_http_error(404, {"Retry-After": "3"})) is None
    assert _retry_after_seconds(_http_error(403, {"Retry-After": "not-a-number"})) is None


def test_describe_http_error_surfaces_the_real_rate_limit_reset_time():
    # Found in an ecosystem-wide software-improvements audit: every
    # HTTPError used to become the same opaque "HTTP {code}", including
    # GitHub's own primary rate limit.
    exc = _http_error(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1700000000"})
    message = describe_http_error(exc)
    assert "rate limited by GitHub" in message
    assert "2023-11-14" in message  # 1700000000 UTC
    assert "GITHUB_TOKEN" in message


def test_describe_http_error_falls_back_for_a_real_access_restriction():
    # A 403 that is NOT the rate limit (X-RateLimit-Remaining absent or
    # nonzero) must stay the plain, generic message - this is a real
    # access restriction, not a transient, actionable rate limit.
    assert describe_http_error(_http_error(403)) == "HTTP 403"
    assert describe_http_error(_http_error(403, {"X-RateLimit-Remaining": "5"})) == "HTTP 403"
    assert describe_http_error(_http_error(404)) == "HTTP 404"


def test_urlopen_with_retries_reads_module_constants_by_default(monkeypatch):
    # `_fetch_one`/`_fetch_discovered_manifest`/`discover_remote_projects`
    # never override max_attempts/backoff_base_s - they rely entirely on
    # the module-level constants. This proves those constants are read at
    # call time (so a test - or a future config option - can change them)
    # rather than baked into the function signature at import time.
    monkeypatch.setattr(github_client, "RETRY_MAX_ATTEMPTS", 2)

    attempts: list[int] = []

    def opener(request, timeout):
        attempts.append(len(attempts) + 1)
        raise urllib.error.URLError("connection refused")

    request = urllib.request.Request("http://example.invalid/manifest")
    with pytest.raises(urllib.error.URLError):
        _urlopen_with_retries(request, timeout=1, opener=opener, sleep=lambda _s: None)

    assert len(attempts) == 2


def test_fetch_one_retries_a_real_unreachable_host_before_reporting_network_error(monkeypatch):
    # End-to-end proof (real socket stack, no fake opener) that _fetch_one
    # really does retry a transient network failure - 127.0.0.1:1 is a
    # real, permanently refused connection - before giving up and
    # reporting it, using the module constants sped up so the test does
    # not spend real retry wall-clock time.
    monkeypatch.setattr(github_client, "RETRY_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(github_client, "RETRY_BACKOFF_BASE_S", 0.01)

    unreachable = "http://127.0.0.1:1/hydra-umc.project.json"
    monkeypatch.setattr(github_client, "github_raw_url", lambda _entry: unreachable)
    monkeypatch.setattr(github_client, "github_native_version_url", lambda _entry: unreachable)

    entry = ProjectEntry("HYDRA-UMC-EXAMPLE", "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)")
    status = _fetch_one(entry)

    assert status.version is None
    assert status.error is not None
