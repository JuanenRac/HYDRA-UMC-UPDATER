# =============================================================================
# HYDRA-UMC-UPDATER - Clone/pull + delegate to each project's own build
# script: install.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Deliberately does NOT reimplement per-stack build logic (npm/cargo/go/
# gradlew/flutter/pip, 7 different toolchains across the ecosystem). Every
# project carries the common non-versioning build-test.sh/.bat entry point.
# It delegates to its own stack-aware check without incrementing a manifest or
# CHANGELOG, so fleet maintenance cannot manufacture a release merely by
# refreshing a checkout. Versioned build scripts remain an explicit human
# release action and are never selected here. The shared build-test entry point
# already knows its own real
# dependencies, venv/toolchain setup, and quirks (HYDRA-UMC-TELEMETRY-
# COLLECTOR/HYDRA-UMC-TOOL-CLI's module root being src/, not the repo
# root, for instance). Reimplementing that here would mean two places that
# both claim to know how to build a given project, guaranteed to drift.
# This module's own job ends at "clone/pull the source, then run whichever
# build script this specific checkout actually has."
# =============================================================================
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2, copytree, ignore_patterns, rmtree
from typing import Callable, Iterable, Mapping
from uuid import uuid4

from . import settings
from .evidence import installed_state, record_attempt
from .project_manifest import ManifestValidationError, ProjectManifest, parse_manifest
from .registry import ProjectEntry, github_repo_url

# P01/the durable version of this module's own in-process
# self-heal for the narrow gap between the 2 promotion renames below (see
# clone_or_pull's own docstring) - HYDRA-UMC-SDK's promotion_journal
# module, shared with HYDRA-UMC-OPS-AGENT's own canary_deploy.py, exactly
# as that fix's own comment called for. Optional (see pyproject.toml's
# own "durable-journal" extra) so this project's safety-critical update
# core stays usable with zero external dependencies - the SAME
# stdlib-only-by-default / opt-in-extra shape this module's own PySide6
# GUI dependency already established. Without it installed, promotion
# still works exactly as before (the in-process self-heal already in
# clone_or_pull), just without surviving a full process crash.
#
# P01/the same optional package also carries check_service_health -
# when a project's own manifest declares a real service_port +
# service_health_path, a promotion is not reported as a real success
# until that real endpoint answers healthy (see _health_check_url_for()
# and clone_or_pull's own promotion step below), and a crash between
# promoting and checking is itself recoverable via
# recover_interrupted_promotions() (the pending check runs for real on
# the next call, never repeating the build).
try:
    from hydra_umc_sdk.promotion_journal import PromotionJournal, PromotionPhase
    from hydra_umc_sdk.promotion_journal import check_service_health as _check_service_health
    from hydra_umc_sdk.promotion_journal import recover as _recover_promotions
    _HAS_DURABLE_JOURNAL = True
except ImportError:
    _HAS_DURABLE_JOURNAL = False

# One journal file per workspace, not per project - a single small JSON
# file covers however many projects this workspace ever promotes,
# consistent with PromotionJournal's own "proportionate for a handful of
# records" design.
_JOURNAL_FILENAME = ".hydra_umc_updater_promotion_journal.json"


# Refuse to run a candidate's build-test script unless the commit that would be
# built carries a signature `git verify-commit` accepts. A build-test script is
# code the candidate brings with it, run on this machine before anything has
# proven the commit is the maintainer's, so a signature is the only thing that
# stands between a rewritten upstream and a shell. Off by default because
# verifying needs a keyring that trusts the maintainer's key (gpg or ssh
# `allowedSignersFile`) configured on this machine. It is switched on either by
# this environment variable or by the saved `require_signed_commits` setting;
# a settings file that exists but cannot be read counts as "required" so a
# damaged file never silently turns the gate off.
REQUIRE_SIGNED_ENV = "HYDRA_UMC_UPDATER_REQUIRE_SIGNED"

#: How long one git command may run before it is abandoned, and the same for a
#: project's own build-test script. A command waiting for credentials or a hung
#: toolchain must not leave a window "working" forever.
GIT_TIMEOUT_S = 300
BUILD_TIMEOUT_S = 1800

#: Per-workspace lock file; held while a project is being installed or updated.
LOCK_FILENAME = ".hydra_umc_updater.lock"


RECREATE_VENV_ENV = "HYDRA_UMC_UPDATER_RECREATE_VENV"


def recreate_venv_enabled() -> bool:
    """A fresh `.venv` after a promotion is the default; HYDRA_UMC_UPDATER_RECREATE_VENV=0 (or the saved setting) turns it off."""
    value = os.environ.get(RECREATE_VENV_ENV, "").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    return settings.get_recreate_venv()


def _python_for_venv() -> str | None:
    """The interpreter that creates a virtual environment: the one running this updater, or, when it is a frozen application, one found on the PATH."""
    if not getattr(sys, "frozen", False):
        return sys.executable
    for name in ("python3", "python", "py"):
        found = shutil.which(name)
        if found:
            return found
    return None


def recreate_venv(checkout: Path, previous: Path, *, progress: ProgressCallback | None = None) -> InstallResult:
    """Gives a promoted checkout a fresh `.venv` when the installation it replaces had one.

    A virtual environment holds absolute paths and the packages of the old sources, so it is never
    carried over. The old one stays in the backup next to the previous checkout. A project that
    had no `.venv` is left alone. Packages come from `requirements.txt` when the project has one.
    """
    if not (previous / ".venv").is_dir():
        return InstallResult(True, "no .venv in the previous installation; nothing to recreate", "")
    python = _python_for_venv()
    if python is None:
        return InstallResult(False, "no Python interpreter was found to create the .venv", "")
    _checkpoint(progress, "validation", "Creating a fresh .venv for the promoted checkout; the previous one stays in the backup.")
    venv = checkout / ".venv"
    if venv.exists():
        _rmtree_best_effort(venv)
    created = _run([python, "-m", "venv", str(venv)], checkout, capture_output=True, timeout=600)
    output = _command_output(created)
    if created.returncode != 0:
        return InstallResult(False, f"could not create the .venv (exit {created.returncode})", output)
    requirements = checkout / "requirements.txt"
    if requirements.is_file():
        interpreter = venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
        installed = _run([str(interpreter), "-m", "pip", "install", "-r", "requirements.txt"], checkout, capture_output=True, timeout=1800)
        output += _command_output(installed)
        if installed.returncode != 0:
            return InstallResult(False, f"the .venv was created but its packages could not be installed (exit {installed.returncode})", output)
    return InstallResult(True, "fresh .venv created", output)


def signature_required() -> bool:
    if os.environ.get(REQUIRE_SIGNED_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return settings.get_require_signed_commits()


def verify_candidate_signature(staging_path: Path) -> tuple[bool, str]:
    """Asks git whether HEAD of the staging clone (the accepted candidate) has a
    valid signature. Returns (ok, detail); a missing gpg/ssh tool, an unsigned
    commit and a signature by an unknown key all come back as not ok. When an
    allowed-signers file is saved in the settings, ssh signatures are checked
    against it."""
    cmd = ["git"]
    signers = settings.get_allowed_signers_file()
    if signers:
        cmd += ["-c", f"gpg.ssh.allowedSignersFile={signers}"]
    cmd += ["verify-commit", "HEAD"]
    result = _run(cmd, cwd=staging_path, capture_output=True, timeout=GIT_TIMEOUT_S)
    detail = _command_output(result).strip()
    if result.returncode != 0:
        return False, detail or f"git verify-commit exited {result.returncode}"
    return True, detail


def _health_check_url_for(entry: ProjectEntry) -> str | None:
    """this project's own real 'servicio comprobado' target - only ever built when
    the project's own manifest declares BOTH `service_port` and
    `service_health_path` (see ProjectEntry's own field comments); either
    alone declares nothing checkable. Always `127.0.0.1`: this checks
    whatever is listening on THIS host, immediately after THIS host's own
    checkout was just promoted - never a remote address a manifest could
    otherwise smuggle in. A project whose real runtime lives elsewhere
    (e.g. deployed separately to /opt/hydra-umc/<svc> and restarted by
    HYDRA-UMC-OS's own provisioning scripts, not served directly from this
    checkout) simply should not declare `service_health_path` in a context
    where checking it here wouldn't mean anything - that is the project's
    own manifest to author, not a judgment call this function makes."""
    if entry.service_port is None or not entry.service_health_path:
        return None
    return f"http://127.0.0.1:{entry.service_port}{entry.service_health_path}"


def recover_interrupted_promotions(workspace_root: Path) -> list[str]:
    """Heals any promotion this updater itself started and never finished
    - a real process crash, `kill -9`, power loss, or a reboot exactly
    between the 2 renames in clone_or_pull's own promotion step. Called
    once at the start of install_or_update() (every real entry point -
    CLI, Tkinter GUI, Qt GUI - funnels through it), so a genuinely
    interrupted prior run is healed before another update ever proceeds.

    Returns the human-readable actions recover() took (empty if nothing
    was pending, OR if hydra-umc-sdk itself isn't installed - see this
    module's own header comment for why that is a real, honest no-op
    rather than an error)."""
    if not _HAS_DURABLE_JOURNAL:
        return []
    journal = PromotionJournal(workspace_root / _JOURNAL_FILENAME)
    return _recover_promotions(journal)


# Checked in this order - the first one that exists in the checkout is the
# one actually run. Covers every real name used across the 44 projects
# (see this module's own header comment) without needing a per-project
# override in registry.py for something this mechanical.
BUILD_TEST_SCRIPT_POSIX = "build-test.sh"
BUILD_TEST_SCRIPT_WINDOWS = "build-test.bat"

# The GUI consumes these events to show the same real work that the CLI does.
# A callback is deliberately optional: command-line users retain normal child
# process output, while the GUI captures it so Windows never needs a second
# terminal window merely to show a project's build output.
ProgressCallback = Callable[[str, str], None]


@dataclass
class InstallResult:
    ok: bool
    message: str
    output: str = ""


def _child_env() -> dict[str, str]:
    """Environment for every git command and build script: never let git or a
    credential helper stop and wait for someone to type, since no one is
    looking at a terminal when the GUI runs this."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    return env


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value if isinstance(value, str) else ""


def _run(
    cmd: list[str], cwd: Path, *, capture_output: bool = False, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Runs one child process and never raises for the usual failures: a
    missing executable comes back as exit 127 and a command that outlives
    `timeout` as exit 124, each with an explanation in stderr, so every caller
    reports it as an ordinary failed step instead of dying with a traceback."""
    kwargs: dict[str, object] = {"cwd": str(cwd), "check": False, "env": _child_env()}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if capture_output:
        kwargs.update({"capture_output": True, "text": True})
    # The GUI is started with pythonw on Windows. Do not let git or a child
    # build script create a surprise console while its output is captured for
    # the in-window checkpoint log.
    if capture_output and os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        # Ecosystem .bat files deliberately finish with `pause` when an
        # operator double-clicks them.  In the GUI they run as a child with
        # captured evidence instead, so provide one harmless newline and do
        # not leave a hidden child waiting forever for a keypress.
        kwargs["input"] = "\n"
    try:
        return subprocess.run(cmd, **kwargs)  # type: ignore[arg-type]
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd, 124, _text(exc.stdout), f"{_text(exc.stderr)}\ntimed out after {int(timeout or 0)} s".strip()
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", f"could not run {cmd[0]}: {exc}")


def _make_writable_and_retry(function: Callable[[str], object], target: str, *_ignored: object) -> None:
    """rmtree error handler: git leaves its pack and index files read-only on
    Windows, which makes every delete fail with a permission error. Make the
    file and its folder writable and try that one removal again."""
    try:
        os.chmod(target, stat.S_IRWXU)
        os.chmod(os.path.dirname(target) or ".", stat.S_IRWXU)
        function(target)
    except OSError:
        pass


def _rmtree_best_effort(path: Path) -> None:
    """Removes a staging directory this module created and no longer
    needs, tolerating the Windows-specific rough edges: a child process (git,
    or a project's own build-test.sh/.bat) can leave a file handle open
    for a brief moment even after that process has already exited, and git
    marks its pack files read-only. The read-only files are made writable and
    the whole removal is retried a few times with a short pause. This is
    always best-effort cleanup of OUR OWN temporary directory, never
    something that should fail the caller's own real result."""
    for attempt in range(5):
        try:
            if sys.version_info >= (3, 12):
                rmtree(path, onexc=_make_writable_and_retry)
            else:
                rmtree(path, onerror=_make_writable_and_retry)
        except FileNotFoundError:
            return
        except OSError:
            pass
        if not path.exists():
            return
        if attempt < 4:
            time.sleep(0.2)


class WorkspaceBusyError(RuntimeError):
    """Another updater process is working in this workspace right now."""


class WorkspaceLock:
    """Exclusive, non-blocking lock on one file in the workspace. Two windows,
    a window and the command line, or this tool and a canary deploy by another
    tool all go through the same promotion renames and the same journal file;
    only one of them may do that at a time."""

    def __init__(self, workspace_root: Path):
        self._path = workspace_root / LOCK_FILENAME
        self._handle = None

    def acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self._path, "a+b")  # noqa: SIM115 - kept open for as long as the lock is held
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise WorkspaceBusyError(
                f"another install or update is already running in {self._path.parent}"
            ) from exc
        self._handle = handle

    def release(self) -> None:
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            handle.close()


def _checkpoint(progress: ProgressCallback | None, phase: str, message: str) -> None:
    if progress is not None:
        progress(phase, message)


# well-known
# build-artifact directory names, never carried over by
# _carry_over_local_data() below even though git genuinely considers
# them untracked/ignored - always safe to regenerate, and carrying them
# over would risk a large, slow copy that also contaminates the staging
# clone's own freshly-verified build with stale artifacts. Same real
# convention this ecosystem's own generic tools/build_test.py already
# excludes when walking a checkout.
_NEVER_CARRIED_OVER_DIR_NAMES = {
    ".git", "node_modules", "dist", "build", "target", ".venv", "venv",
    "__pycache__", ".next", ".cache", ".pytest_cache", ".mypy_cache",
}


def _real_untracked_paths(path: Path) -> list[str]:
    """Returns every real path (relative to `path`) this checkout's own
    git considers untracked OR ignored (`git status`'s own `??`/`!!`
    codes) - the exact real local-data shape needs carried over
    into a staging clone, which `git clone --local` never copies (it
    only ever copies the committed object database). Deliberately never
    includes a modified TRACKED file - a genuinely dirty working tree on
    a tracked file already fails clone_or_pull's own `git merge
    --ff-only` step separately, a different real problem this is not
    trying to solve."""
    result = _run(
        # "matching" lists an ignored folder as itself (`web/node_modules/`)
        # instead of folding it into its parent (`web/`), so a build
        # directory nested inside a folder with real data is still recognised.
        ["git", "status", "--porcelain", "--ignored=matching", "-z"],
        cwd=path, capture_output=True, timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    paths: list[str] = []
    for entry in result.stdout.split("\0"):
        if len(entry) < 4:
            continue
        status_code, rel_path = entry[:2], entry[3:]
        if status_code in ("??", "!!"):
            paths.append(rel_path)
    return paths


class DirtyCheckError(RuntimeError):
    """(shared with HYDRA-UMC-OPS-AGENT's own sibling helper): `git
    status` itself failed to run against a checkout (not a git
    repository, git missing from PATH, a permissions/IO error, ...) -
    see `_tracked_dirty_paths()`'s own docstring for why this must never
    be read as "no dirty files found". Nothing was touched."""


def _tracked_dirty_paths(path: Path) -> list[str]:
    """Returns every real path (relative to `path`) this checkout's own
    git considers a TRACKED file with a real uncommitted change - staged
    or not (`git status --porcelain`'s own status codes other than
    `??`/`!!`, which _real_untracked_paths() already owns).

    this
    module's own docstring used to claim "a real local edit... fails
    loudly with git's own error instead of being silently discarded" -
    true only for the older verify_build=False in-place `git merge
    --ff-only` path. Once moved the default (verify_build=True)
    flow to an isolated staging clone, that claim silently stopped being
    true: `git clone --local` only ever copies the COMMITTED object
    database, so a real uncommitted edit to an already-tracked file
    lives ONLY in `path`'s own working tree and is invisible to the
    fresh, clean staging clone - its own `git merge --ff-only` always
    succeeds (nothing there conflicts), the build succeeds, and
    promotion renames the dirty original aside to `.backup`, so the
    real edit survives only there while this function's own caller
    still reports `ok=True`. Checked explicitly, upfront, so this can
    fail loudly again before any staging work happens at all - matching
    what the docstring already promised.

    (P0, shared with OPS-AGENT's own sibling helper): a `git
    status` that fails to even RUN (returncode != 0) used to be treated
    exactly like "ran fine, found nothing dirty" - the one real
    uncommitted edit this function exists to catch became invisible the
    moment the check itself broke. Raises DirtyCheckError instead: not
    being able to verify clean is not the same as clean."""
    result = _run(
        ["git", "status", "--porcelain", "-z"],
        cwd=path, capture_output=True, timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise DirtyCheckError(
            f"could not verify {path} has no uncommitted changes - `git status` itself failed "
            f"(exit {result.returncode}): {result.stderr.strip() or '(no stderr)'}"
        )
    if not result.stdout:
        return []
    paths: list[str] = []
    for entry_text in result.stdout.split("\0"):
        if len(entry_text) < 4:
            continue
        status_code, rel_path = entry_text[:2], entry_text[3:]
        if status_code in ("??", "!!"):
            continue  # real untracked/ignored data - _carry_over_local_data()'s own concern, not a rejection reason
        paths.append(rel_path)
    return paths


class CarryOverError(RuntimeError):
    """A local data file could not be copied into the candidate checkout."""


def _carry_over_local_data(old_path: Path, staging_path: Path, *, progress: ProgressCallback | None = None) -> None:
    """Copies every real untracked/ignored file or directory from
    `old_path` into `staging_path` before the candidate is built or
    promoted.

    a real
    project's own operational data living inside its checkout (`data/
    settings.json`, `data/users.json`, a real sqlite file, TLS material a
    project generated for itself, ...) is exactly the shape of file `git
    clone --local` never copies at all - it only ever copies the
    committed object database. Reproduced with a real untracked file
    dropped into a real git checkout before an update: the promoted
    checkout was missing it entirely afterward, while the (kept, never
    deleted) `.backup` checkout still had it - a real, silent data loss
    on every update of a project that keeps any real local state inside
    its own checkout, which describes most services in this ecosystem
    (see this module's own header comment on why relocating that data
    outside every checkout entirely is real, separate, future work this
    fix does not attempt)."""
    carried = 0
    for rel_path in _real_untracked_paths(old_path):
        # Regenerable build output is skipped wherever it sits in the path
        # (`web/node_modules`, `clients/python/.venv`, `src/x/__pycache__`...),
        # not only at the top level.
        if any(part in _NEVER_CARRIED_OVER_DIR_NAMES for part in rel_path.rstrip("/").split("/")):
            continue
        source = old_path / rel_path
        if not source.exists() and not source.is_symlink():
            continue  # a real race (removed between `git status` and now) - nothing left to carry
        destination = staging_path / rel_path
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir() and not source.is_symlink():
                # symlinks=True: a link is recreated as a link, never followed
                # into whatever (possibly huge, possibly outside) it points at.
                copytree(
                    source, destination, symlinks=True, dirs_exist_ok=True,
                    ignore=ignore_patterns(*_NEVER_CARRIED_OVER_DIR_NAMES),
                )
            else:
                copy2(source, destination, follow_symlinks=False)
        except OSError as exc:
            raise CarryOverError(
                f"could not carry the local file {rel_path!r} over to the new checkout "
                f"({type(exc).__name__}: {exc}) - it may belong to another user or be in use"
            ) from exc
        carried += 1
    if carried:
        _checkpoint(
            progress, "validation",
            f"Carried {carried} real local data file(s)/director(y/ies) from the installed checkout into the verified candidate.",
        )


def _validated_manifest_text(text: str, entry: ProjectEntry) -> ProjectManifest:
    """Parse the repository-owned manifest used as an update precondition.

    The updater never treats a Git revision as deployable merely because it
    can be fetched. It must still identify itself as the project selected by
    the operator and retain a valid public manifest.
    """
    return parse_manifest(text, expected_name=entry.name)


def _version_tuple(manifest: ProjectManifest) -> tuple[int, int, int, int]:
    parts = [int(part) for part in manifest.version.split(".")]
    parts += [0] * (4 - len(parts))  # a missing fourth component compares as 0
    return tuple(parts)  # type: ignore[return-value]


def _manifest_from_revision(path: Path, revision: str, entry: ProjectEntry) -> ProjectManifest:
    """Read a manifest from Git without modifying the working tree."""
    result = _run(
        ["git", "show", f"{revision}:hydra-umc.project.json"],
        cwd=path,
        capture_output=True,
        timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise ManifestValidationError("candidate revision has no readable hydra-umc.project.json")
    return _validated_manifest_text(result.stdout, entry)


def _local_only_commits(path: Path) -> list[str]:
    """One-line summaries of the commits in `path` that the just-fetched
    FETCH_HEAD does not contain. A checkout that carries such a commit can
    never be fast-forwarded, whatever the working tree looks like."""
    result = _run(
        ["git", "log", "--oneline", "-n", "50", "FETCH_HEAD..HEAD"],
        cwd=path, capture_output=True, timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_running_from(path: Path) -> bool:
    """True when this very process was started from inside `path`."""
    try:
        Path(__file__).resolve().relative_to(path.resolve())
    except ValueError:
        return False
    return True


def clone_or_pull(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    verify_build: bool = True,
    progress: ProgressCallback | None = None,
) -> InstallResult:
    """git clone if this project isn't checked out yet under
    workspace_root, otherwise `git -C <path> fetch` followed by a real
    `git merge --ff-only FETCH_HEAD` - never a force-push-style reset.
    Before that fast-forward, the updater validates the fetched revision's
    repository-owned manifest and rejects a lower version, so an update
    cannot silently become a rollback. A real local edit a developer made
    (this tool is meant to also run on a dev machine, not only the real
    CM5) fails loudly instead of being silently discarded - explicitly
    checked upfront (see _tracked_dirty_paths()'s own docstring for why
    this can no longer be left to git's own `merge --ff-only` error:
    that used to be true, but stopped being true the moment verify_build
    defaulted to the isolated staging-clone flow below, ).

    (P1):
    updating an EXISTING checkout used to merge the candidate straight
    into `path`, then leave building it to a separate step
    (install_or_update's own run_build_script call) - a build failure
    there left new sources merged into `path` sitting next to the
    PREVIOUS build's artifacts, an inconsistent install with no rollback.
    With verify_build=True (the default), the candidate is instead
    cloned+merged+built in a fully independent staging clone FIRST -
    `path` is never touched at all until that build actually succeeds -
    then promoted into place via two back-to-back directory renames
    (each individually atomic on the same filesystem; the previous
    installation is kept, not deleted, at `<name>.backup`, so an
    operator can restore it by hand if the new version misbehaves
    despite building fine). A build failure - or a crash, full disk, or
    diverged/dirty checkout at any point before that final promotion -
    leaves `path` completely untouched and still the operative
    installation. verify_build=False skips all of this and restores the
    exact old in-place-merge behavior, for a caller that intentionally
    doesn't want a build (matching install_or_update's own `build=False`
    path)."""
    path = workspace_root / entry.name
    _checkpoint(progress, "preflight", "Validating the selected workspace and project manifest.")
    if not path.exists():
        # Clone to a sibling staging path first.  A failed network transfer or
        # malformed remote must not leave a partial directory that the next
        # operator run mistakes for a real installation.  rename() is atomic
        # inside workspace_root and we never remove a path we did not create.
        staging_path = workspace_root / f".{entry.name}.clone-{uuid4().hex}"
        _checkpoint(progress, "source", "Cloning the selected repository into a safe staging directory.")
        result = _run(
            ["git", "clone", github_repo_url(entry), str(staging_path)],
            cwd=workspace_root,
            capture_output=progress is not None,
            timeout=GIT_TIMEOUT_S,
        )
        if result.returncode != 0:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"git clone failed (exit {result.returncode})", _command_output(result))
        try:
            _checkpoint(progress, "validation", "Validating the fetched repository manifest before deployment.")
            _manifest_from_revision(staging_path, "HEAD", entry)
        except ManifestValidationError as exc:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"cloned checkout failed manifest validation: {exc}")
        if signature_required():
            # The first install runs the project's own build-test script just
            # like an update does, so it goes through the same gate: nothing
            # unsigned is moved into place, let alone built.
            _checkpoint(progress, "signature", "Verifying the signature of the cloned commit before running anything it brings.")
            signed, signature_detail = verify_candidate_signature(staging_path)
            if not signed:
                _rmtree_best_effort(staging_path)
                return InstallResult(
                    False,
                    f"the cloned commit has no valid signature ({REQUIRE_SIGNED_ENV} or the saved setting requires one) - "
                    "nothing was built or run, and nothing was installed",
                    signature_detail,
                )
        if path.exists():
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"{path} appeared while cloning - not replacing it")
        try:
            staging_path.replace(path)
        except OSError as exc:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"could not move the cloned checkout into place: {type(exc).__name__}: {exc}")
        _checkpoint(progress, "validation", "Manifest accepted; staged checkout promoted without replacing other files.")
        return InstallResult(True, f"Cloned into {path}")

    if not (path / ".git").is_dir():
        return InstallResult(False, f"{path} exists but isn't a git checkout - not touching it")

    try:
        _checkpoint(progress, "preflight", "Validating the installed repository manifest.")
        installed = _manifest_from_revision(path, "HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"installed checkout failed manifest validation: {exc}")

    # refuse upfront, before any fetch/staging work, if a real
    # tracked file has a genuine uncommitted edit - see
    # _tracked_dirty_paths()'s own docstring for exactly why the
    # staging-clone flow below can no longer be trusted to catch this
    # itself. Applies to both verify_build values - a caller intending
    # the older in-place-merge path (verify_build=False) never wanted
    # a real local edit silently discarded either.
    try:
        dirty = _tracked_dirty_paths(path)
    except DirtyCheckError as exc:
        return InstallResult(False, str(exc))
    if dirty:
        preview = ", ".join(dirty[:5]) + (f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else "")
        return InstallResult(
            False,
            f"{path} has uncommitted change(s) to real tracked file(s): {preview} - refusing to update; "
            "commit, stash, or discard them first so an update can never silently discard real local work",
        )

    # Fetch first and inspect FETCH_HEAD before changing the operator's
    # working tree. This prevents a malformed or older remote manifest from
    # becoming an installed downgrade merely because Git can fast-forward it.
    _checkpoint(progress, "source", "Fetching the remote candidate without changing the local checkout.")
    result = _run(
        ["git", "fetch", "--quiet", "origin", "HEAD"],
        cwd=path,
        capture_output=progress is not None,
        timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        return InstallResult(
            False,
            f"git fetch failed (exit {result.returncode}) - remote unavailable or authentication failed?",
            _command_output(result),
        )
    try:
        _checkpoint(progress, "validation", "Checking the candidate manifest and anti-rollback rule.")
        candidate = _manifest_from_revision(path, "FETCH_HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"remote candidate failed manifest validation: {exc}")
    if _version_tuple(candidate) < _version_tuple(installed):
        return InstallResult(
            False,
            f"remote candidate v{candidate.version} is older than installed v{installed.version}; anti-rollback refused update",
        )

    local_only = _local_only_commits(path)
    if local_only:
        listing = "; ".join(local_only[:5]) + (f" (+{len(local_only) - 5} more)" if len(local_only) > 5 else "")
        return InstallResult(
            False,
            f"git merge --ff-only failed: {path} has {len(local_only)} local commit(s) that the upstream does not have "
            f"({listing}), so the update cannot be a fast-forward - move those commits to a branch of their own or "
            f"discard them; {path} was not modified",
        )
    if _is_running_from(path) and sys.platform == "win32":
        return InstallResult(
            False,
            f"{entry.name} is running from {path}, and Windows cannot replace a folder that is in use - close it and "
            "run the update from a copy of the updater that lives outside this checkout",
        )

    if not verify_build:
        _checkpoint(progress, "validation", "Applying the accepted candidate with a fast-forward-only merge.")
        result = _run(
            ["git", "merge", "--ff-only", "FETCH_HEAD"],
            cwd=path,
            capture_output=progress is not None,
            timeout=GIT_TIMEOUT_S,
        )
        if result.returncode != 0:
            return InstallResult(
                False,
                f"git merge --ff-only failed (exit {result.returncode}) - local changes or a diverged branch?",
                _command_output(result),
            )
        return InstallResult(True, f"Pulled latest into {path}")

    # prove the candidate actually builds in a fully independent
    # staging clone BEFORE touching `path` at all - see this function's
    # own docstring. Resolved as a real SHA (not the name "FETCH_HEAD",
    # which means something different in every repo) BEFORE staging even
    # exists: `path`'s FETCH_HEAD already names this exact commit, and
    # `git clone --local` below copies `path`'s whole object database, so
    # that commit is already a real, present object in the staging clone
    # even though nothing there points to it yet - no second fetch
    # needed, and no dependency on staging's own "origin" (which `git
    # clone` would otherwise point at `path` itself, not path's real
    # upstream - fetching "origin" there would silently fetch nothing
    # new and validate the WRONG, stale candidate).
    candidate_sha = _run(
        ["git", "rev-parse", "FETCH_HEAD"], cwd=path, capture_output=True, timeout=GIT_TIMEOUT_S
    ).stdout.strip()
    if not candidate_sha:
        return InstallResult(False, f"could not resolve the fetched candidate to a real commit; {path} was not modified")

    staging_path = workspace_root / f".{entry.name}.update-{uuid4().hex}"
    _checkpoint(progress, "source", "Cloning the installed checkout into an isolated staging area for verification.")
    # --no-hardlinks: a plain `git clone --local` hardlinks object files
    # from `path` on the same volume by default - real, reproducible
    # testing on Windows found that a build script running INSIDE the
    # staging clone can leave those hardlinked objects genuinely
    # undeletable afterward (WinError 5, not a transient lock - retrying
    # does not help), silently leaving an orphaned `.{name}.update-*`
    # directory behind in workspace_root forever. A full copy costs a
    # little more local disk I/O (still no network - this is a same-
    # filesystem clone either way) in exchange for staging actually being
    # a fully independent directory that can always be cleaned up.
    result = _run(
        ["git", "clone", "--local", "--no-hardlinks", str(path), str(staging_path)],
        cwd=workspace_root,
        capture_output=progress is not None,
        timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"could not create a staging clone for verification (exit {result.returncode}); {path} was not modified",
            _command_output(result),
        )

    # `git
    # clone --local` above points the new clone's own `origin` remote at
    # the LOCAL SOURCE PATH it was cloned from (`path`, the installation
    # about to be renamed aside) - never at this project's real GitHub
    # upstream. Left uncorrected, the checkout this staging clone becomes
    # once promoted below would have `origin` pointing at itself, so
    # every FUTURE `git fetch origin` here would fetch nothing new,
    # silently and permanently stopping this checkout from ever
    # discovering a real update again. Reset to the real upstream
    # immediately, before build/promotion, so staging is a faithful
    # preview of the checkout it is about to become in every respect,
    # not just source content.
    real_origin_url = github_repo_url(entry)
    result = _run(
        ["git", "remote", "set-url", "origin", real_origin_url],
        cwd=staging_path, capture_output=progress is not None, timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"could not restore the real upstream remote on the staging clone (exit {result.returncode}); {path} was not modified",
            _command_output(result),
        )

    # carry
    # over the installed checkout's own real local data BEFORE building/
    # promoting - see _carry_over_local_data()'s own docstring for the
    # real gap this closes. Done before the build below (not merely
    # before promotion) so a build-test script that reads this project's
    # own real local files during verification sees the same real data
    # the promoted checkout will actually run against.
    try:
        _carry_over_local_data(path, staging_path, progress=progress)
    except CarryOverError as exc:
        _rmtree_best_effort(staging_path)
        return InstallResult(False, f"{exc}; {path} was not modified")

    _checkpoint(progress, "validation", "Applying the accepted candidate in the isolated staging clone.")
    result = _run(
        ["git", "merge", "--ff-only", candidate_sha],
        cwd=staging_path, capture_output=progress is not None, timeout=GIT_TIMEOUT_S,
    )
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"git merge --ff-only failed (exit {result.returncode}) in a staging clone - local changes or a diverged branch? {path} was not modified.",
            _command_output(result),
        )

    if signature_required():
        _checkpoint(progress, "signature", "Verifying the signature of the candidate commit before running anything it brings.")
        signed, signature_detail = verify_candidate_signature(staging_path)
        if not signed:
            _rmtree_best_effort(staging_path)
            return InstallResult(
                False,
                f"candidate commit {candidate_sha[:12]} has no valid signature ({REQUIRE_SIGNED_ENV} is set) - "
                f"nothing was built or run, and {path} was left completely untouched",
                signature_detail,
            )
    _checkpoint(progress, "build", "Building and verifying the candidate in isolation before touching the live installation.")
    build_result = _run_build_script_at(staging_path, progress=progress)
    if not build_result.ok:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"candidate build failed - {path} was left completely untouched and remains the operative installation: {build_result.message}",
            build_result.output,
        )

    # The one real promotion step: swap the previous installation aside
    # (kept, never deleted - see this function's own docstring) and move
    # the proven-buildable staging clone into its place. Both are plain
    # directory renames on the same filesystem/volume, so each one
    # individually is atomic; the only remaining unsafe window is the
    # brief gap between these two renames (a crash exactly there would
    # leave `path` genuinely missing) - vastly narrower than before,
    # where the unsafe window spanned the entire build.
    #
    # (P1; honest,
    # bounded mitigation, not the full transactional journal/rollback
    # the finding's own acceptance criteria describes - that needs
    # designing once, shared with HYDRA-UMC-OPS-AGENT's own
    # canary_deploy.py, as real, separate future work): two real gaps
    # existed here. First, `backup_path` reused the SAME fixed name
    # every promotion (`rmtree(backup_path, ...)` right before renaming
    # into it) - a second install after a first one already failed
    # partway would silently delete the ONLY recoverable copy of the
    # previous installation before even attempting the new promotion.
    # Now unique per attempt (`.backup-<uuid>`, matching OPS-AGENT's own
    # fix), never overwriting an earlier backup. Second, a crash or
    # exception in the narrow gap between the two renames used to leave
    # NO active checkout at `path` at all, with no attempt to recover -
    # now a best-effort self-heal: if the second rename fails, this
    # immediately tries to rename the backup back to `path` so a real
    # installation still exists, rather than silently leaving neither a
    # live checkout nor a clear indication of which path holds the real
    # one.
    backup_path = workspace_root / f"{entry.name}.backup-{uuid4().hex[:8]}"
    # P01/a durable journal entry, written to disk BEFORE the
    # first real rename, so recover_interrupted_promotions() can heal
    # this promotion even if the process itself dies right here - the
    # in-process self-heal below still runs unconditionally either way,
    # this is additive, never a replacement for it. journal is None
    # (never referenced past this point) when hydra-umc-sdk isn't
    # installed - see this module's own header comment.
    health_check_url = _health_check_url_for(entry)
    journal = PromotionJournal(workspace_root / _JOURNAL_FILENAME) if _HAS_DURABLE_JOURNAL else None
    promotion_id = journal.begin(entry.name, path, staging_path, backup_path, health_check_url=health_check_url).promotion_id if journal else None
    _checkpoint(progress, "validation", "Promoting the verified candidate; the previous installation is kept as a backup.")
    try:
        path.rename(backup_path)
    except OSError as exc:
        # Typically Windows: a program (a service, a terminal, an editor, an
        # antivirus scan) has a file of the installed checkout open. Nothing
        # has moved, so the installation is exactly as it was.
        _rmtree_best_effort(staging_path)
        if journal:
            journal.complete(promotion_id)
        return InstallResult(
            False,
            f"could not move the installed {path} aside ({type(exc).__name__}: {exc}) - close every program that is "
            f"using it and try again; the installation was left exactly as it was",
            build_result.output,
        )
    if journal:
        journal.advance(promotion_id, PromotionPhase.BACKED_UP)
    try:
        staging_path.rename(path)
    except OSError as exc:
        try:
            backup_path.rename(path)
        except OSError:
            return InstallResult(
                False,
                f"promotion failed AND the self-heal restore also failed - {path} may not exist right now; "
                f"the previous installation should still be recoverable at {backup_path}: {exc}",
                build_result.output,
            )
        if journal:
            # The in-process self-heal above already fully resolved this -
            # nothing left for a later recover_interrupted_promotions()
            # call to do.
            journal.complete(promotion_id)
        return InstallResult(
            False,
            f"promotion failed (exit path unavailable: {exc}) - restored the previous installation at {path}; "
            f"the verified candidate is still available at {staging_path} for manual inspection",
            build_result.output,
        )
    if journal:
        journal.advance(promotion_id, PromotionPhase.PROMOTED)
    sha_label = candidate_sha[:12]
    # The promoted checkout gets its own fresh .venv; the previous one stays inside the backup.
    if recreate_venv_enabled():
        venv_result = recreate_venv(path, backup_path, progress=progress)
        if not venv_result.ok:
            return InstallResult(
                False,
                f"Promoted {path} to v{candidate.version} (commit {sha_label}), but its .venv could not be recreated: "
                f"{venv_result.message}. The previous installation, with its own .venv, is kept at {backup_path}",
                venv_result.output or build_result.output,
            )
    # a promotion that finishes its 2 renames is not yet a HEALTHY
    # promotion when the project itself declares a real health endpoint -
    # check it for real before ever calling this a success, rather than
    # treating "the files moved" as the whole postcondition. Skipped
    # entirely (same as before this feature existed) when the project
    # declares no health endpoint, or the optional durable-journal
    # dependency isn't installed at all (no journal to even record the
    # check against - see this module's own header comment).
    if journal and health_check_url:
        healthy, reason = _check_service_health(health_check_url)
        if not healthy:
            return InstallResult(
                False,
                f"Promoted {path} to v{candidate.version} (commit {sha_label}), but its own declared health "
                f"check at {health_check_url} still fails ({reason}). This updater does not restart services, so "
                f"restart whatever runs from this checkout and check it again; the previous installation is kept at "
                f"{backup_path}",
                build_result.output,
            )
        journal.complete(promotion_id)
        return InstallResult(
            True,
            f"Updated {path} to v{candidate.version} (commit {sha_label}) after a verified build and a real "
            f"passing health check ({reason}); previous installation kept at {backup_path}",
            build_result.output,
        )
    if journal:
        journal.complete(promotion_id)
    return InstallResult(
        True,
        f"Updated {path} to v{candidate.version} (commit {sha_label}) after a verified build; "
        f"previous installation kept at {backup_path}",
        build_result.output,
    )


def find_build_test_script(path: Path) -> Path | None:
    name = BUILD_TEST_SCRIPT_WINDOWS if os.name == "nt" else BUILD_TEST_SCRIPT_POSIX
    candidate = path / name
    return candidate if candidate.is_file() else None


def run_build_script(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    progress: ProgressCallback | None = None,
) -> InstallResult:
    return _run_build_script_at(workspace_root / entry.name, progress=progress)


def _run_build_script_at(path: Path, *, progress: ProgressCallback | None = None) -> InstallResult:
    """The real work behind run_build_script(), taking an explicit path
    instead of deriving one from workspace_root/entry.name - shared with
    clone_or_pull's own staging-clone build verification, which
    needs to build a candidate sitting in a temporary staging directory,
    not (yet) the real installed checkout."""
    script = find_build_test_script(path)
    if script is None:
        return InstallResult(False, f"No non-versioning build-test.sh/.bat found in {path} - upgrade this checkout or verify it manually before deployment.")

    if os.name == "nt":
        cmd = ["cmd", "/c", str(script)]
    else:
        cmd = ["bash", str(script)]

    _checkpoint(progress, "build", f"Running {script.name}; this never increments the project version.")
    result = _run(cmd, cwd=path, capture_output=progress is not None, timeout=BUILD_TIMEOUT_S)
    if result.returncode == 124:
        return InstallResult(
            False,
            f"{script.name} was stopped after {BUILD_TIMEOUT_S} s without finishing.",
            _command_output(result),
        )
    if result.returncode != 0:
        return InstallResult(
            False,
            f"{script.name} exited with code {result.returncode} - see the in-window evidence below for what failed.",
            _command_output(result),
        )
    return InstallResult(True, f"{script.name} completed successfully.", _command_output(result))


#: Projects that must go first and last when several are handled in one batch:
#: the SDK is imported by many others, and the updater replaces the very
#: program that is running the batch.
BATCH_FIRST = ("HYDRA-UMC-SDK",)
BATCH_LAST = ("HYDRA-UMC-UPDATER",)


def batch_order_key(name: str) -> tuple[int, str]:
    """Sort key for a batch of installs or updates (see BATCH_FIRST/LAST)."""
    if name in BATCH_FIRST:
        return (0, name.casefold())
    if name in BATCH_LAST:
        return (2, name.casefold())
    return (1, name.casefold())


def order_batch(names: list[str], depends_on: Mapping[str, Iterable[str]] | None = None) -> list[str]:
    """The order a batch handles `names` in: the SDK first and the updater last
    (batch_order_key), and every project after the ones it declares in `depends_on`
    that are part of the same batch. Names a project depends on that are not in the
    batch are ignored. A cycle cannot be ordered: its members keep the plain order."""
    base = sorted(names, key=batch_order_key)
    if not depends_on:
        return base
    in_batch = set(base)
    wanted = {name: {dep for dep in depends_on.get(name, ()) if dep in in_batch and dep != name} for name in base}
    ordered: list[str] = []
    done: set[str] = set()
    pending = list(base)
    while pending:
        pick = next((name for name in pending if wanted[name] <= done), pending[0])
        pending.remove(pick)
        ordered.append(pick)
        done.add(pick)
    return ordered


def format_batch_list(names: list[str], limit: int = 40, depends_on: Mapping[str, Iterable[str]] | None = None) -> str:
    """The exact, ordered list a batch confirmation shows: one numbered name per line.

    More than `limit` names are cut with a final line that says how many were left out,
    so the dialog stays readable while the count shown there is still the real one.
    """
    ordered = order_batch(names, depends_on)
    lines = [f"{index}. {name}" for index, name in enumerate(ordered[:limit], start=1)]
    if len(ordered) > limit:
        lines.append(f"... +{len(ordered) - limit}")
    return "\n".join(lines)


#: A staging directory this updater left behind (a crash, a power cut, an
#: undeletable file) is removed once it is clearly not in use any more.
ORPHAN_STAGING_AGE_S = 2 * 60 * 60

_STAGING_MARKERS = (".update-", ".clone-")
_BACKUP_NAME = re.compile(r"^(?P<name>.+)\.backup-[0-9a-f]{8}$")


def cleanup_orphaned_staging(workspace_root: Path, *, older_than_s: float = ORPHAN_STAGING_AGE_S) -> list[Path]:
    """Removes the hidden `.<name>.update-*` / `.<name>.clone-*` directories this
    updater creates for staging when they are older than `older_than_s`.
    Returns the directories that are gone afterwards."""
    removed: list[Path] = []
    try:
        entries = list(workspace_root.iterdir())
    except OSError:
        return removed
    now = time.time()
    for entry_path in entries:
        name = entry_path.name
        if not name.startswith(".") or not any(marker in name for marker in _STAGING_MARKERS):
            continue
        try:
            if not entry_path.is_dir() or now - entry_path.stat().st_mtime < older_than_s:
                continue
        except OSError:
            continue
        _rmtree_best_effort(entry_path)
        if not entry_path.exists():
            removed.append(entry_path)
    return removed


def list_backups(workspace_root: Path) -> dict[str, list[Path]]:
    """The `<name>.backup-<8 hex>` directories of the workspace, newest first,
    grouped by project name."""
    groups: dict[str, list[Path]] = {}
    try:
        entries = list(workspace_root.iterdir())
    except OSError:
        return groups
    for entry_path in entries:
        match = _BACKUP_NAME.match(entry_path.name)
        if match and entry_path.is_dir():
            groups.setdefault(match.group("name"), []).append(entry_path)
    for paths in groups.values():
        paths.sort(key=lambda candidate: candidate.stat().st_mtime, reverse=True)
    return groups


def prune_backups(workspace_root: Path, *, keep: int = 2, dry_run: bool = False) -> list[Path]:
    """Keeps the `keep` newest backups of every project and removes the rest.
    Only ever run on an operator's explicit request (`prune-backups`); returns
    the directories that were (or, with `dry_run`, would be) removed."""
    if keep < 0:
        raise ValueError("keep must not be negative")
    removed: list[Path] = []
    for paths in list_backups(workspace_root).values():
        for old in paths[keep:]:
            if dry_run:
                removed.append(old)
                continue
            _rmtree_best_effort(old)
            if not old.exists():
                removed.append(old)
    return removed


def install_or_update(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    build: bool = True,
    progress: ProgressCallback | None = None,
) -> list[InstallResult]:
    """The full manual install/update flow for ONE project - never called
    for more than one project per invocation (see cli.py's own `install`/
    `update` subcommands, which always take an explicit project name, and
    this project's own README for why that is a deliberate, non-optional
    design choice: explicit operator approval keeps deployment safe).

    Updating an EXISTING checkout builds/verifies the candidate itself,
    inside clone_or_pull's own staging clone, BEFORE ever promoting it into
    the real installation - see that function's own docstring. A brand-new
    clone is verified for its signature and manifest in staging, then built
    in its final place (a build that creates a virtual environment would
    otherwise bake the staging path into it); if that build fails, the
    checkout just created is removed again so the project shows as not
    installed rather than as a half-installed one.

    Only one install or update runs in a workspace at a time (a lock file in
    the workspace), and the attempt is always written to the evidence file,
    even when something unexpected goes wrong: an exception becomes a failed
    result, never a window that stays busy forever.

    Heals any promotion a PREVIOUS run of this updater started and never
    finished (a real process crash exactly between clone_or_pull's own 2
    promotion renames) before this run's own work begins - see
    recover_interrupted_promotions()'s own doc comment. A genuine no-op
    when nothing was pending, or when hydra-umc-sdk isn't installed."""
    lock = WorkspaceLock(workspace_root)
    try:
        lock.acquire()
    except (WorkspaceBusyError, OSError) as exc:
        return [InstallResult(False, str(exc))]
    try:
        return _install_or_update_locked(entry, workspace_root, build=build, progress=progress)
    finally:
        lock.release()


def _install_or_update_locked(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    build: bool,
    progress: ProgressCallback | None,
) -> list[InstallResult]:
    path = workspace_root / entry.name
    recovered: list[str] = []
    try:
        recovered = recover_interrupted_promotions(workspace_root)
        cleanup_orphaned_staging(workspace_root)
    except Exception as exc:  # noqa: BLE001 - housekeeping must never stop the real work
        _checkpoint(progress, "preflight", f"Housekeeping before the update failed ({type(exc).__name__}: {exc}); continuing.")
    for action in recovered:
        _checkpoint(progress, "preflight", f"Recovered an interrupted promotion: {action}")
    was_existing_checkout = (path / ".git").is_dir()
    before = installed_state(path)
    results: list[InstallResult] = []
    try:
        results.append(clone_or_pull(entry, workspace_root, verify_build=build, progress=progress))
        if results[0].ok and build and not was_existing_checkout:
            built = run_build_script(entry, workspace_root, progress=progress)
            results.append(built)
            if not built.ok:
                _rmtree_best_effort(path)
                removed = "the new checkout was removed again" if not path.exists() else "the new checkout could not be removed"
                results.append(InstallResult(False, f"the build of the fresh install failed, so {removed}"))
        elif results[0].ok and build:
            _checkpoint(progress, "build", "Build already verified in an isolated staging clone before promotion.")
        elif results[0].ok:
            _checkpoint(progress, "build", "Build-test was deliberately skipped for this one approved source refresh.")
    except Exception as exc:  # noqa: BLE001 - every failure is reported, none may escape to a worker thread
        results.append(InstallResult(False, f"unexpected failure: {type(exc).__name__}: {exc}"))
    finally:
        message = "; ".join(r.message for r in results) or "no result"
        if recovered:
            message += "; recovered: " + ", ".join(recovered)
        record_attempt(
            workspace_root,
            project=entry.name,
            before=before,
            after=installed_state(path),
            ok=bool(results) and all(r.ok for r in results),
            message=message,
        )
    return results


#: The newest part of a child's output that is kept as evidence; a compiler
#: log can be megabytes long and the window only shows the last few lines.
OUTPUT_LIMIT = 20_000


def _command_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return compact child evidence when a GUI captured it, at most the last
    OUTPUT_LIMIT characters of it."""
    text = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if len(text) > OUTPUT_LIMIT:
        text = "... (earlier output omitted)\n" + text[-OUTPUT_LIMIT:]
    return text
