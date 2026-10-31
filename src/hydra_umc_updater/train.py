# =============================================================================
# HYDRA-UMC-UPDATER - Version trains: train.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Version trains: a tested set of versions of the repositories, installed together.

A train is a JSON file with the version and the exact commit of each repository (the shape of the family's
`ecosystem-release.json`, with optional extra fields per repository). Instead of taking the head of every repository
on its own, the updater can install the train: it first checks that the train is well formed and consistent, that
every pinned commit is part of the published history of its repository and that the manifest there says the listed
version, and only then installs what differs, in the order of `depends_on`. Before the first change it saves what was
installed, so the previous train can be put back.

The whole feature is off unless the switch is on (`version_trains` in the saved settings or
`HYDRA_UMC_UPDATER_TRAINS=1`); planning is read-only and the default of `apply` and `rollback` is a dry run.

File shape (`schema_version` "1.0"; every key not listed here is refused, a malformed train installs nothing)::

    {"schema_version": "1.0", "ecosystem": "HYDRA-UMC", "name": "...",          # name optional
     "digest": "<sha256 of the canonical repositories list>",                   # optional
     "repositories": [{"name": "HYDRA-UMC-SDK", "version": "0.3.6", "commit": "<40 hex>",
                       "manifest_sha256": "<sha256 of hydra-umc.project.json at that commit>",   # optional
                       "depends_on": ["HYDRA-UMC-SDK"],                         # optional, must match the manifest
                       "requires_min": {"HYDRA-UMC-SDK": "0.3.0"}}]}            # optional minimum versions
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import settings
from .evidence import installed_state
from .install import (
    GIT_TIMEOUT_S,
    InstallResult,
    PinSpec,
    ProgressCallback,
    _check_pin,
    _run,
    _tracked_dirty_paths,
    DirtyCheckError,
    install_or_update,
    order_batch,
)
from .registry import ProjectEntry

SCHEMA_VERSION = "1.0"
ECOSYSTEM = "HYDRA-UMC"
TRAINS_ENV = "HYDRA_UMC_UPDATER_TRAINS"
STATE_DIR = ".hydra-umc-trains"
PREVIOUS_FILE = "previous.json"
CURRENT_FILE = "current.json"

_NAME = re.compile(r"^HYDRA-UMC(-[A-Z0-9-]+)?$")
_VERSION = re.compile(r"^\d+(?:\.\d+){2,3}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOP_KEYS = {"schema_version", "ecosystem", "name", "digest", "repositories"}
_REPO_KEYS = {"name", "version", "commit", "manifest_sha256", "depends_on", "requires_min"}


class TrainError(ValueError):
    """A train file that is malformed, inconsistent or whose digest does not match."""


@dataclass(frozen=True)
class TrainRepo:
    name: str
    version: str
    commit: str
    manifest_sha256: str | None = None
    depends_on: tuple[str, ...] | None = None
    requires_min: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Train:
    name: str
    repos: tuple[TrainRepo, ...]
    digest: str | None = None

    def by_name(self) -> dict[str, TrainRepo]:
        return {repo.name: repo for repo in self.repos}


def version_key(value: str) -> tuple[int, ...]:
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (4 - len(parts))


def canonical_digest(repositories: list[object]) -> str:
    """sha256 of the repositories list written canonically (sorted keys, no spaces, ASCII)."""
    text = json.dumps(repositories, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def trains_enabled() -> bool:
    """The switch. Off by default; a damaged settings file also means off."""
    value = os.environ.get(TRAINS_ENV, "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    if settings.settings_file_is_damaged():
        return False
    return settings.load_settings().get("version_trains") is True


def _fail(message: str) -> TrainError:
    return TrainError(message)


def parse_train(text: str, *, default_name: str = "train") -> Train:
    """Parse a train and refuse anything that is not exactly the documented shape."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise _fail(f"the train is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise _fail("the train must be a JSON object")
    unknown = set(data) - _TOP_KEYS
    if unknown:
        raise _fail(f"unknown key(s) in the train: {', '.join(sorted(unknown))}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise _fail(f"schema_version must be {SCHEMA_VERSION!r}")
    if data.get("ecosystem") != ECOSYSTEM:
        raise _fail(f"ecosystem must be {ECOSYSTEM!r}")
    name = data.get("name", default_name)
    if not isinstance(name, str) or not name.strip():
        raise _fail("name must be a non-empty string")
    raw_repos = data.get("repositories")
    if not isinstance(raw_repos, list) or not raw_repos:
        raise _fail("repositories must be a non-empty list")
    digest = data.get("digest")
    if digest is not None:
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise _fail("digest must be 64 lowercase hex characters")
        if canonical_digest(raw_repos) != digest:
            raise _fail("the digest of the train does not match its repositories (the file was changed)")
    repos: list[TrainRepo] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_repos):
        where = f"repositories[{index}]"
        if not isinstance(raw, dict):
            raise _fail(f"{where} must be an object")
        extra = set(raw) - _REPO_KEYS
        if extra:
            raise _fail(f"{where}: unknown key(s): {', '.join(sorted(extra))}")
        repo_name, version, commit = raw.get("name"), raw.get("version"), raw.get("commit")
        if not isinstance(repo_name, str) or not _NAME.match(repo_name):
            raise _fail(f"{where}: name must be a HYDRA-UMC repository name")
        if repo_name in seen:
            raise _fail(f"{where}: {repo_name} is listed twice")
        seen.add(repo_name)
        if not isinstance(version, str) or not _VERSION.match(version):
            raise _fail(f"{repo_name}: version must look like 1.2.3 or 1.2.3.4")
        if not isinstance(commit, str) or not _COMMIT.match(commit):
            raise _fail(f"{repo_name}: commit must be a full 40-character lowercase commit id")
        manifest_sha = raw.get("manifest_sha256")
        if manifest_sha is not None and (not isinstance(manifest_sha, str) or not _SHA256.match(manifest_sha)):
            raise _fail(f"{repo_name}: manifest_sha256 must be 64 lowercase hex characters")
        depends = raw.get("depends_on")
        if depends is not None:
            if (
                not isinstance(depends, list)
                or any(not isinstance(item, str) or not _NAME.match(item) for item in depends)
                or len(set(depends)) != len(depends)
                or repo_name in depends
            ):
                raise _fail(f"{repo_name}: depends_on must be a list of unique other repository names")
        requires = raw.get("requires_min", {})
        if not isinstance(requires, dict) or any(
            not isinstance(key, str) or not _NAME.match(key) or not isinstance(value, str) or not _VERSION.match(value)
            for key, value in requires.items()
        ):
            raise _fail(f"{repo_name}: requires_min must map repository names to versions")
        if repo_name in requires:
            raise _fail(f"{repo_name}: requires_min must not name the repository itself")
        repos.append(
            TrainRepo(repo_name, version, commit, manifest_sha, tuple(depends) if depends is not None else None, dict(requires))
        )
    return Train(name.strip(), tuple(sorted(repos, key=lambda repo: repo.name)), digest)


def load_train(path: Path) -> Train:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TrainError(f"cannot read the train {path}: {exc}") from exc
    return parse_train(text, default_name=path.stem)


def train_to_json(train: Train) -> str:
    """The train as a file (with its digest), in the shape `parse_train` reads."""
    repositories: list[object] = []
    for repo in train.repos:
        item: dict[str, object] = {"name": repo.name, "version": repo.version, "commit": repo.commit}
        if repo.manifest_sha256:
            item["manifest_sha256"] = repo.manifest_sha256
        if repo.depends_on is not None:
            item["depends_on"] = list(repo.depends_on)
        if repo.requires_min:
            item["requires_min"] = dict(repo.requires_min)
        repositories.append(item)
    data = {
        "schema_version": SCHEMA_VERSION,
        "ecosystem": ECOSYSTEM,
        "name": train.name,
        "digest": canonical_digest(repositories),
        "repositories": repositories,
    }
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


# ---------------------------------------------------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class PlanItem:
    name: str
    action: str  # install | update | downgrade | keep | blocked
    version: str
    commit: str
    installed_version: str | None
    installed_commit: str | None
    reason: str

    def as_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass
class Plan:
    train: Train
    items: list[PlanItem]
    problems: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def changes(self) -> list[PlanItem]:
        return [item for item in self.items if item.action in {"install", "update", "downgrade"}]

    def as_dict(self) -> dict[str, object]:
        return {
            "train": self.train.name,
            "ok": self.ok,
            "problems": list(self.problems),
            "items": [item.as_dict() for item in self.items],
        }


def _installed(workspace_root: Path, name: str) -> tuple[str | None, str | None, bool]:
    path = workspace_root / name
    if not path.is_dir():
        return None, None, False
    state = installed_state(path)
    return state.get("version"), state.get("commit"), True


def _check_compatibility(train: Train, workspace_root: Path) -> list[str]:
    """Everything that can be said about a train from the file and the installed versions, before any fetch."""
    problems: list[str] = []
    by_name = train.by_name()

    def version_of(name: str) -> str | None:
        if name in by_name:
            return by_name[name].version
        return _installed(workspace_root, name)[0]

    for repo in train.repos:
        for dep, minimum in sorted(repo.requires_min.items()):
            have = version_of(dep)
            if have is None:
                problems.append(f"{repo.name} needs {dep} >= {minimum}, which is neither in the train nor installed")
            elif version_key(have) < version_key(minimum):
                problems.append(f"{repo.name} needs {dep} >= {minimum}, but the train would leave {have}")
        for dep in repo.depends_on or ():
            if dep not in by_name and _installed(workspace_root, dep)[2] is False:
                problems.append(f"{repo.name} depends on {dep}, which is neither in the train nor installed")
    graph = {repo.name: [dep for dep in (repo.depends_on or ()) if dep in by_name] for repo in train.repos}
    ordered = order_batch(list(graph), graph)
    position = {name: index for index, name in enumerate(ordered)}
    cyclic = sorted({name for name, deps in graph.items() for dep in deps if position[dep] > position[name]})
    if cyclic:
        problems.append("depends_on forms a cycle between: " + ", ".join(cyclic))
    return problems


FetchFunction = Callable[[Path], tuple[bool, str]]


def fetch_origin(path: Path) -> tuple[bool, str]:
    result = _run(["git", "fetch", "--quiet", "origin", "HEAD"], cwd=path, capture_output=True, timeout=GIT_TIMEOUT_S)
    return result.returncode == 0, (result.stderr or "").strip()


def plan_train(
    train: Train,
    workspace_root: Path,
    *,
    allow_downgrade: bool = False,
    fetch: FetchFunction | None = fetch_origin,
) -> Plan:
    """Explain what installing the train would do, and why, changing nothing in any working tree.

    Installed repositories that differ from the train are fetched (only the Git objects are updated, never the
    files) so the pinned commit can be checked against the published history and its manifest. A repository that is
    not installed yet cannot be checked before it is cloned: its checks run at install time, and a failing one
    installs nothing. `fetch=None` plans without the network (a pinned commit that is not already here is then a
    problem, never assumed)."""
    problems = _check_compatibility(train, workspace_root)
    items: list[PlanItem] = []
    by_name = train.by_name()
    for repo in train.repos:
        version, commit, present = _installed(workspace_root, repo.name)
        path = workspace_root / repo.name
        if present and not (path / ".git").is_dir():
            reason = f"{path} exists but is not a Git checkout; it will not be touched"
            items.append(PlanItem(repo.name, "blocked", repo.version, repo.commit, version, commit, reason))
            problems.append(f"{repo.name}: {reason}")
            continue
        if not present:
            items.append(PlanItem(
                repo.name, "install", repo.version, repo.commit, None, None,
                f"not installed; clones it and puts it on v{repo.version} ({repo.commit[:12]}), checked after the clone",
            ))
            continue
        if commit == repo.commit:
            items.append(PlanItem(repo.name, "keep", repo.version, repo.commit, version, commit, "already on the commit of the train"))
            continue
        item_problems: list[str] = []
        try:
            dirty = _tracked_dirty_paths(path)
        except DirtyCheckError as exc:
            dirty = []
            item_problems.append(str(exc))
        if dirty:
            item_problems.append("has uncommitted changes to tracked files: " + ", ".join(dirty[:5]))
        entry = ProjectEntry(repo.name, "", "", "")
        if fetch is not None:
            fetched, detail = fetch(path)
            if not fetched:
                item_problems.append(f"could not fetch the repository to check the commit ({detail or 'remote unavailable'})")
        if not item_problems:
            upstream = "FETCH_HEAD" if fetch is not None else "HEAD"
            manifest, problem = _check_pin(path, PinSpec(repo.commit, repo.version, repo.manifest_sha256), entry, upstream)
            if manifest is None:
                item_problems.append(problem or "the pinned commit could not be checked")
            else:
                declared = tuple(manifest.depends_on)
                if repo.depends_on is not None and tuple(sorted(repo.depends_on)) != tuple(sorted(declared)):
                    item_problems.append("depends_on in the train differs from the manifest at that commit")
                for dep in declared:
                    if dep not in by_name and not _installed(workspace_root, dep)[2]:
                        item_problems.append(f"the manifest depends on {dep}, which is neither in the train nor installed")
        if item_problems:
            reason = "; ".join(item_problems)
            items.append(PlanItem(repo.name, "blocked", repo.version, repo.commit, version, commit, reason))
            problems.append(f"{repo.name}: {reason}")
            continue
        older = version is not None and version_key(repo.version) < version_key(version)
        if older and not allow_downgrade:
            reason = f"installed v{version} is newer than v{repo.version} of the train; going back needs --allow-downgrade"
            items.append(PlanItem(repo.name, "blocked", repo.version, repo.commit, version, commit, reason))
            problems.append(f"{repo.name}: {reason}")
            continue
        if older:
            action, reason = "downgrade", f"goes back from v{version} to v{repo.version} ({repo.commit[:12]})"
        else:
            action, reason = "update", f"differs from the train: v{version} ({(commit or '')[:12]}) -> v{repo.version} ({repo.commit[:12]})"
        items.append(PlanItem(repo.name, action, repo.version, repo.commit, version, commit, reason))
    graph = {repo.name: list(repo.depends_on or ()) for repo in train.repos}
    rank = {name: index for index, name in enumerate(order_batch([repo.name for repo in train.repos], graph))}
    items.sort(key=lambda item: rank[item.name])
    return Plan(train, items, problems)


def format_plan(plan: Plan, *, dry_run: bool) -> str:
    lines = [f"Train {plan.train.name!r}: {len(plan.train.repos)} repositories, {len(plan.changes)} to change"]
    for index, item in enumerate(plan.items, start=1):
        lines.append(f"{index:>3}. {item.action.upper():<9} {item.name} - {item.reason}")
    if plan.problems:
        lines.append("")
        lines.append("Nothing will be installed: the train has problems.")
        lines.extend(f"  - {problem}" for problem in plan.problems)
    elif dry_run:
        lines.append("")
        lines.append("Dry run: nothing was installed. Repeat with --yes (and the version_trains switch on) to install.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------------------------
# State, apply, rollback
# ---------------------------------------------------------------------------------------------------------------------

def state_dir(workspace_root: Path) -> Path:
    return workspace_root / STATE_DIR


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def snapshot_installed(train: Train, workspace_root: Path, name: str) -> Train | None:
    """What is installed now for the repositories of `train`, as a train (None when none is installed)."""
    repos: list[TrainRepo] = []
    for repo in train.repos:
        version, commit, present = _installed(workspace_root, repo.name)
        if present and version and commit and _VERSION.match(version) and _COMMIT.match(commit):
            repos.append(TrainRepo(repo.name, version, commit))
    return Train(name, tuple(repos)) if repos else None


@dataclass
class ApplyOutcome:
    ok: bool
    applied: list[str] = field(default_factory=list)
    failed: str | None = None
    messages: list[str] = field(default_factory=list)


Installer = Callable[..., list[InstallResult]]


def apply_train(
    plan: Plan,
    workspace_root: Path,
    entries: Mapping[str, ProjectEntry],
    *,
    build: bool = True,
    progress: ProgressCallback | None = None,
    installer: Installer = install_or_update,
    remember: bool = True,
) -> ApplyOutcome:
    """Install what differs, in dependency order, stopping at the first failure.

    A plan with problems installs nothing. Before the first change the installed state of every repository of the
    train is saved (`previous.json`), so `rollback_train` can put it back, including after a failure half way."""
    if not plan.ok:
        return ApplyOutcome(False, messages=["the plan has problems; nothing was installed"])
    missing = [item.name for item in plan.changes if item.name not in entries]
    if missing:
        return ApplyOutcome(False, messages=["unknown project(s), nothing was installed: " + ", ".join(missing)])
    if not plan.changes:
        return ApplyOutcome(True, messages=["every repository is already on the commit of the train"])
    if remember:
        previous = snapshot_installed(plan.train, workspace_root, f"before {plan.train.name}")
        if previous is not None:
            _write_atomic(state_dir(workspace_root) / PREVIOUS_FILE, train_to_json(previous))
    outcome = ApplyOutcome(True)
    for item in plan.changes:
        pin = PinSpec(item.commit, item.version, _manifest_digest_of(plan.train, item.name), allow_downgrade=item.action == "downgrade")
        results = installer(entries[item.name], workspace_root, build=build, progress=progress, pin=pin)
        outcome.messages.extend(f"{item.name}: {r.message}" for r in results)
        if not results or not all(r.ok for r in results):
            outcome.ok, outcome.failed = False, item.name
            outcome.messages.append(
                f"stopped at {item.name}; the ones before it stay installed. `train rollback` puts the previous state back."
            )
            return outcome
        outcome.applied.append(item.name)
    if remember:
        _write_atomic(state_dir(workspace_root) / CURRENT_FILE, train_to_json(plan.train))
    return outcome


def _manifest_digest_of(train: Train, name: str) -> str | None:
    return train.by_name()[name].manifest_sha256


def load_previous(workspace_root: Path) -> Train | None:
    path = state_dir(workspace_root) / PREVIOUS_FILE
    if not path.is_file():
        return None
    return load_train(path)


def mark_rolled_back(workspace_root: Path) -> None:
    """The saved state was used: keep it under another name (nothing is ever deleted) so it is not applied twice."""
    source = state_dir(workspace_root) / PREVIOUS_FILE
    target = state_dir(workspace_root) / f"rolled-back-{os.getpid()}-{int(source.stat().st_mtime)}.json"
    os.replace(source, target)
