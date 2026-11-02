# =============================================================================
# HYDRA-UMC-UPDATER - Evidence export: evidence_export.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Hand the evidence of the update attempts to the rest of the fleet.

`evidence.jsonl` is what this machine did. Exporting turns each line into an
envelope that is chained to the one before it (every envelope carries the sha256
of its content and the sha256 of the previous envelope), appends it to an outbox
file, and, when the data lake address is set, pushes the new envelopes as samples
of `POST /ingest/batch`. Anyone who gets the outbox (the data lake, the ops agent,
a person with a USB stick) can check with `verify_chain` that no envelope was
changed, removed from the middle or reordered.

Everything is off unless the switch `evidence_export` is on. The outbox is the
source of truth: the position of the next envelope is the number of lines it has,
so a crash between two writes never repeats or skips a line, and the push resends
from the first envelope the data lake has not accepted (the data lake stores a
re-delivered sample once, as its identity is the same). The token of the data lake
is read from a file and is never printed or stored in the settings; plain HTTP to
an address that is not this machine is refused unless the settings allow it."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from . import settings
from .evidence import EVIDENCE_FILE
from .updater_core import HYDRA_PROFILE, EcosystemProfile

OUTBOX_FILE = "evidence-outbox.jsonl"
STATE_FILE = "evidence-export-state.json"
SCHEMA = "hydra-updater-evidence/1"
GENESIS = "0" * 64
#: the data lake refuses a batch of more than 1000 samples by default
PUSH_BATCH = 500
PUSH_TIMEOUT_S = 15.0
#: a timestamp smaller than this is a producer that sent seconds, and the data lake refuses it
MIN_TIMESTAMP_MS = 100_000_000_000


def export_enabled(profile: EcosystemProfile = HYDRA_PROFILE) -> bool:
    """The environment wins over the saved setting; off by default."""
    flag = profile.env_flag("EVIDENCE_EXPORT")
    return flag if flag is not None else settings.get_evidence_export()


def node_name(profile: EcosystemProfile = HYDRA_PROFILE) -> str:
    return profile.env_text("NODE_NAME") or settings.get_node_name() or socket.gethostname() or "unknown-node"


def _directory(workspace_root: Path, profile: EcosystemProfile) -> Path:
    return workspace_root / profile.state_directory


def outbox_path(workspace_root: Path, profile: EcosystemProfile = HYDRA_PROFILE) -> Path:
    return _directory(workspace_root, profile) / OUTBOX_FILE


def _digest(body: dict[str, Any]) -> str:
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_lines(path: Path) -> list[str]:
    try:
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def _parse_record(line: str) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except ValueError:
        return {"unreadable": True}
    return value if isinstance(value, dict) else {"unreadable": True}


def make_envelope(record: dict[str, Any], *, node: str, seq: int, prev: str, now_ms: int) -> dict[str, Any]:
    """One envelope: the record, its place in the chain and the proof of both. A record that has no time of its own (written
    before the evidence file kept one) takes the time of the export and says so in `atEstimated`."""
    at = record.get("at")
    estimated = not (isinstance(at, int) and not isinstance(at, bool) and at >= MIN_TIMESTAMP_MS)
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "node": node,
        "seq": seq,
        "at": now_ms if estimated else at,
        "atEstimated": estimated,
        "record": record,
        "prev": prev,
    }
    body["sha256"] = _digest(body)
    return body


@dataclass(frozen=True)
class ExportResult:
    exported: int
    total: int
    outbox: Path | None
    error: str | None = None


def export_new(
    workspace_root: Path, *, node: str | None = None, now_ms: int | None = None, profile: EcosystemProfile = HYDRA_PROFILE
) -> ExportResult:
    """Append the attempts that are not in the outbox yet. Fails closed: an evidence file shorter than the outbox means it was cut or
    replaced, and nothing is exported until a person looks at it."""
    evidence = _read_lines(_directory(workspace_root, profile) / EVIDENCE_FILE)
    outbox = outbox_path(workspace_root, profile)
    existing = _read_lines(outbox)
    if len(existing) > len(evidence):
        return ExportResult(0, len(evidence), outbox, f"the evidence file has {len(evidence)} lines and the outbox already holds {len(existing)}: it was cut or replaced")
    prev = GENESIS
    if existing:
        last = _parse_record(existing[-1])
        prev = str(last.get("sha256") or "")
        if len(prev) != 64:
            return ExportResult(0, len(evidence), outbox, "the last line of the outbox is damaged; verify it before exporting again")
    moment = int(time.time() * 1000) if now_ms is None else now_ms
    name = node or node_name(profile)
    fresh: list[str] = []
    for index in range(len(existing), len(evidence)):
        envelope = make_envelope(_parse_record(evidence[index]), node=name, seq=index, prev=prev, now_ms=moment)
        prev = envelope["sha256"]
        fresh.append(json.dumps(envelope, sort_keys=True, ensure_ascii=False))
    if not fresh:
        return ExportResult(0, len(evidence), outbox)
    try:
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with outbox.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(fresh) + "\n")
    except OSError as exc:
        return ExportResult(0, len(evidence), outbox, f"the outbox could not be written: {exc}")
    return ExportResult(len(fresh), len(evidence), outbox)


def verify_chain(path: Path) -> tuple[bool, int, str]:
    """Check an outbox (or any copy of it): every envelope matches its own sha256, points at the one before and has the next
    position. Returns (ok, envelopes checked, what is wrong)."""
    lines = _read_lines(path)
    prev = GENESIS
    for index, line in enumerate(lines):
        envelope = _parse_record(line)
        claimed = envelope.pop("sha256", None)
        if claimed != _digest(envelope):
            return False, index, f"envelope {index} does not match its sha256"
        if envelope.get("prev") != prev:
            return False, index, f"envelope {index} does not follow the one before it"
        if envelope.get("seq") != index:
            return False, index, f"envelope {index} is out of place (seq {envelope.get('seq')})"
        prev = str(claimed)
    return True, len(lines), "ok"


def to_samples(envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The envelopes as samples for `POST /ingest/batch`: kind `updater_attempt` from the source `<node>/<project>`, fields `ok` (1 or 0)
    and `seq`; the sequence of the sample is the position in the chain, so two attempts in the same millisecond stay two points."""
    samples = []
    for envelope in envelopes:
        raw_record = envelope.get("record")
        record: dict[str, Any] = raw_record if isinstance(raw_record, dict) else {}
        project = str(record.get("project") or "unknown")
        samples.append(
            {
                "sourceId": f"{envelope.get('node')}/{project}",
                "kind": "updater_attempt",
                "timestamp": envelope["at"],
                "sequence": envelope["seq"],
                "fields": {"ok": 1 if record.get("ok") is True else 0, "seq": envelope["seq"]},
            }
        )
    return samples


def _pushed(workspace_root: Path, profile: EcosystemProfile) -> int:
    try:
        value = json.loads((_directory(workspace_root, profile) / STATE_FILE).read_text(encoding="utf-8")).get("pushed")
    except (OSError, ValueError, AttributeError):
        return 0
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _save_pushed(workspace_root: Path, profile: EcosystemProfile, count: int) -> None:
    path = _directory(workspace_root, profile) / STATE_FILE
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"pushed": count}), encoding="utf-8")
    os.replace(temporary, path)


def _is_this_machine(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_address(url: str, *, allow_plain_http: bool) -> str | None:
    """Why `url` may not receive the evidence, or None when it may."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return "the address of the data lake must be http:// or https:// with a host"
    if parts.username or parts.password:
        return "the address of the data lake must not carry a user or password; the token is read from a file"
    if parts.scheme == "http" and not allow_plain_http and not _is_this_machine(parts.hostname):
        return "plain HTTP to another machine is refused (use https, or allow it with evidence_export_allow_plain_http)"
    return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would send the token to an address nobody checked."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None


def _default_open(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.build_opener(_NoRedirect).open(request, timeout=timeout)


def read_token(token_file: str | None) -> str | None:
    if not token_file:
        return None
    try:
        return Path(token_file).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


@dataclass(frozen=True)
class PushResult:
    pushed: int
    pending: int
    error: str | None = None


def push_pending(
    workspace_root: Path,
    base_url: str,
    *,
    token: str | None = None,
    allow_plain_http: bool = False,
    open_url: Callable[[urllib.request.Request, float], Any] = _default_open,
    batch: int = PUSH_BATCH,
    profile: EcosystemProfile = HYDRA_PROFILE,
) -> PushResult:
    """Send the envelopes the data lake has not accepted yet, in batches; the position is saved after each accepted batch. The chain is
    verified first: a broken outbox is not sent."""
    problem = check_address(base_url, allow_plain_http=allow_plain_http)
    if problem:
        return PushResult(0, 0, problem)
    path = outbox_path(workspace_root, profile)
    ok, _count, detail = verify_chain(path)
    if not ok:
        return PushResult(0, 0, f"the outbox is not a valid chain ({detail}); nothing was sent")
    envelopes = [_parse_record(line) for line in _read_lines(path)]
    start = min(_pushed(workspace_root, profile), len(envelopes))
    pending = envelopes[start:]
    sent = 0
    target = base_url.rstrip("/") + "/ingest/batch"
    while sent < len(pending):
        chunk = pending[sent : sent + max(1, min(batch, 1000))]
        body = json.dumps({"samples": to_samples(chunk)}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(target, data=body, headers=headers, method="POST")
        try:
            with open_url(request, PUSH_TIMEOUT_S) as response:
                status = getattr(response, "status", 0)
        except urllib.error.HTTPError as exc:
            return PushResult(sent, len(pending) - sent, f"the data lake answered {exc.code}")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return PushResult(sent, len(pending) - sent, f"the data lake could not be reached ({type(exc).__name__})")
        if status != 202:
            return PushResult(sent, len(pending) - sent, f"the data lake answered {status}")
        sent += len(chunk)
        try:
            _save_pushed(workspace_root, profile, start + sent)
        except OSError as exc:
            return PushResult(sent, len(pending) - sent, f"the position could not be saved ({exc}); the next push repeats these samples, which the data lake stores once")
    return PushResult(sent, 0)
