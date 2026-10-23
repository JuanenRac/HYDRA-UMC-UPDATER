# =============================================================================
# HYDRA-UMC-UPDATER - tests/test_etag_cache.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Conditional requests for the list of repositories: a 304 reuses the last page and a changed list replaces it. A real
local HTTP server that understands If-None-Match, like GitHub does."""
from __future__ import annotations

import http.server
import json
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from hydra_umc_updater import github_client
from hydra_umc_updater.github_client import EtagCache, default_etag_cache, discover_remote_projects

from test_github_client import valid_manifest


class _ConditionalHandler(http.server.BaseHTTPRequestHandler):
    state: dict = {}

    def log_message(self, format, *args):  # noqa: A002
        pass

    def do_GET(self) -> None:  # noqa: N802
        state = self.state
        state["requests"].append({"path": self.path, "if_none_match": self.headers.get("If-None-Match")})
        if self.path.startswith("/users/"):
            body, etag = state["listing"], state["etag"]
            if etag and self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            self.send_response(200)
            if etag:
                self.send_header("ETag", etag)
        else:
            body = state["manifests"].get(self.path)
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def github_like(listing: list[dict], manifests: dict[str, dict], etag: str | None = '"v1"'):
    state = {
        "listing": json.dumps(listing).encode(),
        "etag": etag,
        "manifests": {path: json.dumps(m).encode() for path, m in manifests.items()},
        "requests": [],
    }
    handler = type("_Handler", (_ConditionalHandler,), {"state": state})
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        thread.join(timeout=5)


MANIFESTS = {"/JuanenRac/GoodProject/main/hydra-umc.project.json": valid_manifest("GoodProject")}
LISTING = [{"name": "GoodProject", "default_branch": "main"}]


def listing_requests(state: dict) -> list[dict]:
    return [r for r in state["requests"] if r["path"].startswith("/users/")]


def test_the_second_run_asks_conditionally_and_gets_the_same_projects_from_a_304(monkeypatch, tmp_path: Path) -> None:
    with github_like(LISTING, MANIFESTS) as (base, state):
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base)
        monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base)
        cache = EtagCache(tmp_path / "etag.json")
        first = discover_remote_projects(cache=cache)
        second = discover_remote_projects(cache=cache)
    requests = listing_requests(state)
    assert [r["if_none_match"] for r in requests] == [None, '"v1"']
    assert [s.entry.name for s in first.projects] == [s.entry.name for s in second.projects] == ["GoodProject"]


def test_a_changed_listing_replaces_the_cached_page(monkeypatch, tmp_path: Path) -> None:
    with github_like(LISTING, MANIFESTS) as (base, state):
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base)
        monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base)
        cache = EtagCache(tmp_path / "etag.json")
        discover_remote_projects(cache=cache)
        state["listing"] = json.dumps(LISTING + [{"name": "OtherProject", "default_branch": "main"}]).encode()
        state["etag"] = '"v2"'
        state["manifests"]["/JuanenRac/OtherProject/main/hydra-umc.project.json"] = json.dumps(valid_manifest("OtherProject")).encode()
        changed = discover_remote_projects(cache=cache)
        again = discover_remote_projects(cache=cache)
    assert sorted(s.entry.name for s in changed.projects) == ["GoodProject", "OtherProject"]
    assert [r["if_none_match"] for r in listing_requests(state)] == [None, '"v1"', '"v2"']
    assert sorted(s.entry.name for s in again.projects) == ["GoodProject", "OtherProject"]


def test_the_cache_survives_a_restart_through_its_file(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "etag.json"
    with github_like(LISTING, MANIFESTS) as (base, state):
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base)
        monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base)
        discover_remote_projects(cache=EtagCache(path))
        again = discover_remote_projects(cache=EtagCache(path))  # a new object reading the file, like a new process
    assert [r["if_none_match"] for r in listing_requests(state)] == [None, '"v1"']
    assert [s.entry.name for s in again.projects] == ["GoodProject"]


def test_without_a_cache_every_request_is_unconditional(monkeypatch) -> None:
    with github_like(LISTING, MANIFESTS) as (base, state):
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base)
        monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base)
        discover_remote_projects()
        discover_remote_projects()
    assert [r["if_none_match"] for r in listing_requests(state)] == [None, None]


def test_an_answer_without_an_etag_is_not_cached(monkeypatch, tmp_path: Path) -> None:
    with github_like(LISTING, MANIFESTS, etag=None) as (base, state):
        monkeypatch.setattr(github_client, "GITHUB_API_BASE", base)
        monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base)
        cache = EtagCache(tmp_path / "etag.json")
        discover_remote_projects(cache=cache)
        discover_remote_projects(cache=cache)
    assert [r["if_none_match"] for r in listing_requests(state)] == [None, None]


def test_a_damaged_or_foreign_cache_file_is_an_empty_cache_not_an_error(tmp_path: Path) -> None:
    for content in ("{not json", json.dumps([1, 2]), json.dumps({"version": 9, "entries": {}}),
                    json.dumps({"version": 1, "entries": {"u": {"etag": 5, "body": "x"}}})):
        path = tmp_path / "etag.json"
        path.write_text(content, encoding="utf-8")
        assert EtagCache(path).get("u") is None


def test_the_cache_is_bounded_and_forgets_the_oldest_first(tmp_path: Path) -> None:
    cache = EtagCache(tmp_path / "etag.json", max_entries=3)
    for index in range(5):
        cache.put(f"u{index}", f'"e{index}"', "body")
    assert [cache.get(f"u{index}") is not None for index in range(5)] == [False, False, True, True, True]


def test_a_cache_file_that_cannot_be_written_is_not_an_error(tmp_path: Path) -> None:
    cache = EtagCache(tmp_path / "missing-folder" / "etag.json")
    cache.put("u", '"e"', "body")
    cache.save()  # no exception: the next run asks in full


def test_the_default_cache_can_be_turned_off(monkeypatch) -> None:
    monkeypatch.setenv("HYDRA_UMC_UPDATER_NO_CACHE", "1")
    cache = default_etag_cache()
    cache.put("u", '"e"', "body")
    cache.save()
    assert cache._path is None
