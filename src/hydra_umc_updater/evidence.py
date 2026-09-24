# =============================================================================
# HYDRA-UMC-UPDATER - src/hydra_umc_updater/evidence.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""One line of evidence for every install or update attempt: which project,
what was installed before, what is installed now, at which commit, and
whether the attempt succeeded. Appended to a JSON-lines file in the
workspace, so a failed or interrupted attempt leaves a trace and a
successful one can be checked later. Recording never raises: a problem
writing the record must not turn a good update into a failed one."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

EVIDENCE_DIRECTORY = ".hydra-umc-updater"
EVIDENCE_FILE = "evidence.jsonl"


def installed_state(project_path: Path) -> dict[str, str | None]:
    """The version and commit of what is installed at `project_path`, or None for each when unknown."""
    version = commit = None
    manifest = project_path / "hydra-umc.project.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        pass
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if completed.returncode == 0:
            commit = completed.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        pass
    return {"version": version, "commit": commit}


def record_attempt(
    workspace_root: Path,
    *,
    project: str,
    before: dict[str, Any],
    after: dict[str, Any],
    ok: bool,
    message: str,
) -> Path | None:
    """Append one attempt to the evidence file; returns its path, or None if it could not be written."""
    line = {
        "project": project,
        "ok": ok,
        "versionBefore": before.get("version"),
        "commitBefore": before.get("commit"),
        "versionAfter": after.get("version"),
        "commitAfter": after.get("commit"),
        "message": message[:500],
    }
    try:
        directory = workspace_root / EVIDENCE_DIRECTORY
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / EVIDENCE_FILE
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(line, sort_keys=True) + "\n")
        return path
    except OSError:
        return None


def read_attempts(workspace_root: Path) -> list[dict[str, Any]]:
    path = workspace_root / EVIDENCE_DIRECTORY / EVIDENCE_FILE
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return []
