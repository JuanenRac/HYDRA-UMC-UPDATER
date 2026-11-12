# =============================================================================
# HYDRA-UMC-UPDATER - GitHub client tests: every way a single lookup can fail, and the scan of many
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The lookup of one project never raises an ordinary network error: each cause becomes a message in the status, and one broken project
does not stop the scan of the others. The transport is replaced by a function, so no socket opens and no wait happens."""
from __future__ import annotations

import email.message
import json
import socket
import urllib.error

import pytest

from hydra_umc_updater import github_client
from hydra_umc_updater.github_client import _fetch_one, fetch_all
from hydra_umc_updater.registry import ProjectEntry

ENTRY = ProjectEntry("HYDRA-UMC-EXAMPLE", "python", "pyproject.toml", r"version = \"(\d+)\.(\d+)\.(\d+)\"")


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://example.invalid/x", code, "error", email.message.Message(), None)


def manifest_text(name: str = ENTRY.name, version: str = "1.4.2") -> bytes:
    return json.dumps(
        {
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
            "native_version": {"file": "pyproject.toml", "pattern": r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"'},
            "build": "python -m build",
            "notes": "Fixture manifest.",
        }
    ).encode()


def serve(monkeypatch, answers):
    """Replace the transport: `answers` is a list of bytes (an answer) or exceptions (raised), one per call; the urls asked are returned."""
    asked: list[str] = []
    queue = list(answers)

    def fake(request, timeout=None, **_kwargs):
        asked.append(request.full_url)
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr(github_client, "_urlopen_with_retries", fake)
    return asked


@pytest.mark.parametrize(
    "failure, expected",
    [
        (urllib.error.URLError("name not known"), "network error: name not known"),
        (TimeoutError(), "timed out after"),
        (socket.timeout(), "timed out after"),
        (OSError("connection reset"), "OS/network error: connection reset"),
        (RuntimeError("boom"), "unexpected error: RuntimeError: boom"),
        (ValueError("odd"), "unexpected error: ValueError: odd"),
    ],
)
def test_each_failure_of_the_transport_becomes_a_message_and_no_version(monkeypatch, failure, expected):
    serve(monkeypatch, [failure])
    status = _fetch_one(ENTRY)
    assert status.version is None
    assert expected in status.error
    assert status.manifest is None
    assert status.url


@pytest.mark.parametrize("code", [403, 429, 500, 502, 503])
def test_an_error_status_other_than_404_is_reported_with_its_code(monkeypatch, code):
    asked = serve(monkeypatch, [http_error(code)])
    status = _fetch_one(ENTRY)
    assert status.http_status == code
    assert status.version is None and status.error
    assert len(asked) == 1  # only a 404 tries the native version file


def test_a_404_falls_back_to_the_native_version_file(monkeypatch):
    asked = serve(monkeypatch, [http_error(404), b'version = "2.5.9"\n'])
    status = _fetch_one(ENTRY)
    assert status.error is None and status.http_status is None
    assert (status.version.major, status.version.minor, status.version.patch) == (2, 5, 9)
    assert len(asked) == 2 and asked[1] != asked[0]


def test_a_404_with_a_native_file_that_has_no_version_is_the_404(monkeypatch):
    serve(monkeypatch, [http_error(404), b"nothing here\n"])
    status = _fetch_one(ENTRY)
    assert status.http_status == 404 and status.version is None


@pytest.mark.parametrize("failure", [urllib.error.URLError("down"), TimeoutError(), OSError("x"), http_error(500)])
def test_a_404_and_then_a_native_file_that_cannot_be_read_is_still_the_404(monkeypatch, failure):
    serve(monkeypatch, [http_error(404), failure])
    status = _fetch_one(ENTRY)
    assert status.http_status == 404 and status.version is None


def test_a_good_manifest_gives_the_version_and_the_manifest(monkeypatch):
    serve(monkeypatch, [manifest_text()])
    status = _fetch_one(ENTRY)
    assert status.error is None
    assert (status.version.major, status.version.minor, status.version.patch) == (1, 4, 2)
    assert status.manifest is not None and status.manifest.name == ENTRY.name


@pytest.mark.parametrize("body", [b"not json at all", b"{}", b"[]", b"\xff\xfe\x00 bytes", manifest_text(name="HYDRA-UMC-OTHER"), manifest_text(version="x.y")])
def test_a_manifest_that_is_not_valid_is_reported_and_never_raised(monkeypatch, body):
    serve(monkeypatch, [body])
    status = _fetch_one(ENTRY)
    assert status.version is None
    assert status.error and "invalid project manifest" in status.error


def test_the_scan_of_nothing_is_nothing_and_calls_no_progress(monkeypatch):
    calls: list[tuple[int, int]] = []
    assert fetch_all([], progress=lambda done, total: calls.append((done, total))) == {}
    assert calls == []


def test_the_scan_reports_every_project_and_the_progress_counts_up(monkeypatch):
    entries = [ProjectEntry(f"HYDRA-UMC-P{i}", "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)") for i in range(5)]
    monkeypatch.setattr(github_client, "_urlopen_with_retries", lambda request, timeout=None, **_k: manifest_text())
    seen: list[tuple[int, int]] = []
    results = fetch_all(entries, progress=lambda done, total: seen.append((done, total)))
    assert sorted(results) == sorted(entry.name for entry in entries)
    assert [done for done, _ in seen] == [1, 2, 3, 4, 5]
    assert {total for _, total in seen} == {5}


def test_a_worker_that_breaks_outside_the_lookup_becomes_a_failure_status(monkeypatch):
    entries = [ProjectEntry("HYDRA-UMC-GOOD", "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)"), ProjectEntry("HYDRA-UMC-BAD", "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)")]

    def fake(entry):
        if entry.name.endswith("BAD"):
            raise RuntimeError("the worker died")
        return github_client.RemoteStatus(entry=entry, version=None, error="fine", url="u")

    monkeypatch.setattr(github_client, "_fetch_one", fake)
    results = fetch_all(entries)
    assert results["HYDRA-UMC-GOOD"].error == "fine"
    assert results["HYDRA-UMC-BAD"].error == "worker failure: RuntimeError: the worker died"
    assert results["HYDRA-UMC-BAD"].version is None
