# =============================================================================
# HYDRA-UMC-UPDATER - evidence export tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from hydra_umc_updater import evidence_export, main, settings
from hydra_umc_updater.evidence import record_attempt
from hydra_umc_updater.updater_core import HYDRA_PROFILE


def _attempts(root: Path, count: int, *, ok: bool = True) -> None:
    for index in range(count):
        record_attempt(root, project=f"P{index}", before={"version": "0.1.0"}, after={"version": "0.1.1"}, ok=ok, message="m")


class _Lake:
    """A local data lake that accepts (or refuses) batches and remembers them."""

    def __init__(self, status: int = 202) -> None:
        self.status = status
        self.batches: list[dict[str, Any]] = []
        self.headers: list[str | None] = []
        lake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                lake.headers.append(self.headers.get("Authorization"))
                if lake.status == 202:
                    lake.batches.append(body)
                self.send_response(lake.status)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def lake():
    created: list[_Lake] = []

    def make(status: int = 202) -> _Lake:
        created.append(_Lake(status))
        return created[-1]

    yield make
    for item in created:
        item.close()


def test_new_attempts_are_chained_and_a_second_export_adds_only_the_new_ones(tmp_path: Path) -> None:
    _attempts(tmp_path, 3)
    first = evidence_export.export_new(tmp_path, node="n1", now_ms=1_800_000_000_000)
    assert (first.exported, first.total, first.error) == (3, 3, None)
    assert evidence_export.verify_chain(evidence_export.outbox_path(tmp_path)) == (True, 3, "ok")
    assert evidence_export.export_new(tmp_path, node="n1").exported == 0
    _attempts(tmp_path, 2)
    assert evidence_export.export_new(tmp_path, node="n1").exported == 2
    ok, count, _ = evidence_export.verify_chain(evidence_export.outbox_path(tmp_path))
    assert ok and count == 5


def test_a_changed_removed_or_reordered_envelope_breaks_the_chain(tmp_path: Path) -> None:
    _attempts(tmp_path, 4)
    evidence_export.export_new(tmp_path, node="n1")
    path = evidence_export.outbox_path(tmp_path)
    lines = path.read_text(encoding="utf-8").splitlines()

    changed = json.loads(lines[1])
    changed["record"]["ok"] = False
    path.write_text("\n".join([lines[0], json.dumps(changed), *lines[2:]]) + "\n", encoding="utf-8")
    assert evidence_export.verify_chain(path)[:2] == (False, 1)

    path.write_text("\n".join([lines[0], *lines[2:]]) + "\n", encoding="utf-8")
    assert evidence_export.verify_chain(path)[0] is False

    path.write_text("\n".join([lines[1], lines[0], *lines[2:]]) + "\n", encoding="utf-8")
    assert evidence_export.verify_chain(path)[0] is False

    path.write_text("not json\n", encoding="utf-8")
    assert evidence_export.verify_chain(path)[0] is False


def test_an_evidence_file_shorter_than_the_outbox_exports_nothing(tmp_path: Path) -> None:
    _attempts(tmp_path, 3)
    evidence_export.export_new(tmp_path, node="n1")
    evidence = tmp_path / HYDRA_PROFILE.state_directory / "evidence.jsonl"
    evidence.write_text(evidence.read_text(encoding="utf-8").splitlines()[0] + "\n", encoding="utf-8")
    result = evidence_export.export_new(tmp_path, node="n1")
    assert result.exported == 0 and result.error and "cut or replaced" in result.error


def test_an_old_line_without_a_time_takes_the_time_of_the_export_and_says_so(tmp_path: Path) -> None:
    directory = tmp_path / HYDRA_PROFILE.state_directory
    directory.mkdir()
    (directory / "evidence.jsonl").write_text(json.dumps({"project": "Old", "ok": True}) + "\n", encoding="utf-8")
    evidence_export.export_new(tmp_path, node="n1", now_ms=1_800_000_000_123)
    (envelope,) = [json.loads(line) for line in evidence_export.outbox_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    assert envelope["at"] == 1_800_000_000_123 and envelope["atEstimated"] is True


def test_the_samples_follow_the_ingest_contract(tmp_path: Path) -> None:
    _attempts(tmp_path, 1, ok=False)
    evidence_export.export_new(tmp_path, node="cm5-a")
    (envelope,) = [json.loads(line) for line in evidence_export.outbox_path(tmp_path).read_text(encoding="utf-8").splitlines()]
    (sample,) = evidence_export.to_samples([envelope])
    assert sample["sourceId"] == "cm5-a/P0" and sample["kind"] == "updater_attempt"
    assert sample["fields"] == {"ok": 0, "seq": 0} and sample["sequence"] == 0
    assert sample["timestamp"] >= evidence_export.MIN_TIMESTAMP_MS


def test_push_sends_batches_with_the_token_and_remembers_the_position(tmp_path: Path, lake) -> None:
    server = lake()
    _attempts(tmp_path, 5)
    evidence_export.export_new(tmp_path, node="n1")
    result = evidence_export.push_pending(tmp_path, server.url, token="secret-token", batch=2)
    assert (result.pushed, result.pending, result.error) == (5, 0, None)
    assert [len(batch["samples"]) for batch in server.batches] == [2, 2, 1]
    assert set(server.headers) == {"Bearer secret-token"}
    # nothing new: nothing is sent again
    assert evidence_export.push_pending(tmp_path, server.url, token="secret-token").pushed == 0
    assert len(server.batches) == 3
    _attempts(tmp_path, 1)
    evidence_export.export_new(tmp_path, node="n1")
    assert evidence_export.push_pending(tmp_path, server.url).pushed == 1


def test_a_refusal_keeps_the_position_so_the_next_push_retries(tmp_path: Path, lake) -> None:
    refusing = lake(status=401)
    _attempts(tmp_path, 2)
    evidence_export.export_new(tmp_path, node="n1")
    result = evidence_export.push_pending(tmp_path, refusing.url)
    assert result.pushed == 0 and result.pending == 2 and result.error and "401" in result.error
    accepting = lake()
    assert evidence_export.push_pending(tmp_path, accepting.url).pushed == 2


def test_a_broken_outbox_is_not_sent(tmp_path: Path, lake) -> None:
    server = lake()
    _attempts(tmp_path, 2)
    evidence_export.export_new(tmp_path, node="n1")
    path = evidence_export.outbox_path(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace('"ok": true', '"ok": false'), encoding="utf-8")
    result = evidence_export.push_pending(tmp_path, server.url)
    assert result.error and "not a valid chain" in result.error and server.batches == []


@pytest.mark.parametrize(
    "url, allow, refused",
    [
        ("http://127.0.0.1:8080", False, False),
        ("http://localhost:8080", False, False),
        ("https://lake.example", False, False),
        ("http://lake.example:8080", False, True),
        ("http://lake.example:8080", True, False),
        ("ftp://lake.example", True, True),
        ("https://user:pw@lake.example", True, True),
        ("lake.example", True, True),
    ],
)
def test_the_address_checks(url: str, allow: bool, refused: bool) -> None:
    assert (evidence_export.check_address(url, allow_plain_http=allow) is not None) is refused


def test_a_redirect_is_not_followed_so_the_token_stays_with_the_checked_address(tmp_path: Path) -> None:
    class Redirecting(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(307)
            self.send_header("Location", "http://127.0.0.1:1/elsewhere")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Redirecting)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _attempts(tmp_path, 1)
        evidence_export.export_new(tmp_path, node="n1")
        result = evidence_export.push_pending(tmp_path, f"http://127.0.0.1:{server.server_address[1]}", token="t")
        assert result.pushed == 0 and result.error and "307" in result.error
    finally:
        server.shutdown()
        server.server_close()


def test_the_token_is_read_from_a_file_only(tmp_path: Path) -> None:
    token = tmp_path / "token"
    token.write_text("abc\n", encoding="utf-8")
    assert evidence_export.read_token(str(token)) == "abc"
    assert evidence_export.read_token(str(tmp_path / "missing")) is None
    assert evidence_export.read_token(None) is None


def test_the_export_is_off_by_default_and_the_environment_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYDRA_UMC_UPDATER_EVIDENCE_EXPORT", raising=False)
    assert evidence_export.export_enabled() is False
    settings.save_evidence_export(True)
    assert evidence_export.export_enabled() is True
    monkeypatch.setenv("HYDRA_UMC_UPDATER_EVIDENCE_EXPORT", "0")
    assert evidence_export.export_enabled() is False


def test_a_damaged_settings_file_keeps_the_export_and_plain_http_off(isolated_settings: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYDRA_UMC_UPDATER_EVIDENCE_EXPORT", raising=False)
    isolated_settings.write_text("[1, 2", encoding="utf-8")
    assert evidence_export.export_enabled() is False
    assert settings.get_evidence_export_allow_plain_http() is False


def test_the_command_refuses_to_export_while_the_switch_is_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("HYDRA_UMC_UPDATER_EVIDENCE_EXPORT", raising=False)
    _attempts(tmp_path, 1)
    args = main.build_parser().parse_args(["evidence", "export", "--workspace", str(tmp_path)])
    code = args.func(args)
    assert code == 1 and not evidence_export.outbox_path(tmp_path).exists()
    assert "switched off" in capsys.readouterr().err


def test_the_command_exports_pushes_and_verifies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lake, capsys: pytest.CaptureFixture[str]) -> None:
    server = lake()
    monkeypatch.setenv("HYDRA_UMC_UPDATER_EVIDENCE_EXPORT", "1")
    token = tmp_path / "token"
    token.write_text("tok", encoding="utf-8")
    _attempts(tmp_path, 2)
    parser = main.build_parser()
    args = parser.parse_args(["evidence", "export", "--workspace", str(tmp_path), "--push", "--url", server.url, "--token-file", str(token)])
    assert args.func(args) == 0
    assert len(server.batches[0]["samples"]) == 2 and server.headers == ["Bearer tok"]
    out = capsys.readouterr().out
    assert "Exported 2 new attempt(s)" in out and "Pushed 2 sample(s)" in out and "tok" not in out
    verify = parser.parse_args(["evidence", "verify", "--workspace", str(tmp_path)])
    assert verify.func(verify) == 0
