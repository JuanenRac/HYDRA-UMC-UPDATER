# =============================================================================
# HYDRA-UMC-UPDATER - Failure handling, locking, signature gate and housekeeping
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hydra_umc_updater import install, main as main_module, settings
from hydra_umc_updater.evidence import EVIDENCE_DIRECTORY, EVIDENCE_FILE
from hydra_umc_updater.install import (
    InstallResult,
    WorkspaceBusyError,
    WorkspaceLock,
    batch_order_key,
    cleanup_orphaned_staging,
    clone_or_pull,
    install_or_update,
    list_backups,
    prune_backups,
)
from hydra_umc_updater.registry import ProjectEntry, github_raw_url
from test_install import _two_commit_checkout, entry, git, write_build_script, write_manifest


def _remote_with_one_release(tmp_path: Path, *, build_ok: bool = True) -> Path:
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=build_ok)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    return remote


# --- child processes never raise and never wait for a person ---------------

def test_a_missing_executable_comes_back_as_a_failed_step(tmp_path: Path):
    result = install._run(["definitely-not-a-real-program-xyz"], cwd=tmp_path, capture_output=True)
    assert result.returncode == 127
    assert "could not run" in result.stderr


def test_a_command_that_runs_too_long_is_stopped(tmp_path: Path):
    started = time.monotonic()
    result = install._run(
        [sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path, capture_output=True, timeout=1
    )
    assert result.returncode == 124
    assert "timed out" in result.stderr
    assert time.monotonic() - started < 20


def test_children_never_wait_for_git_credentials(tmp_path: Path):
    result = install._run(
        [sys.executable, "-c", "import os; print(os.environ['GIT_TERMINAL_PROMPT'], os.environ['GCM_INTERACTIVE'])"],
        cwd=tmp_path, capture_output=True,
    )
    assert result.stdout.split() == ["0", "never"]


def test_the_kept_command_output_is_bounded():
    result = subprocess.CompletedProcess([], 0, "x" * (install.OUTPUT_LIMIT * 3), "")
    text = install._command_output(result)
    assert len(text) < install.OUTPUT_LIMIT + 100
    assert text.endswith("x")
    assert "omitted" in text


# --- an unexpected exception never strands the caller ----------------------

def test_an_unexpected_exception_becomes_a_failed_result_and_is_recorded(tmp_path: Path, monkeypatch):
    def explode(*_args, **_kwargs):
        raise PermissionError("the file belongs to root")

    monkeypatch.setattr(install, "clone_or_pull", explode)

    results = install_or_update(entry(), tmp_path)

    assert [r.ok for r in results] == [False]
    assert "PermissionError" in results[0].message
    evidence = (tmp_path / EVIDENCE_DIRECTORY / EVIDENCE_FILE).read_text(encoding="utf-8").splitlines()
    assert json.loads(evidence[-1])["ok"] is False


def test_git_missing_from_the_path_is_an_ordinary_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "nowhere"))
    remote = tmp_path / "remote.git"
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    results = install_or_update(entry(), tmp_path)
    assert not results[0].ok
    assert not (tmp_path / entry().name).exists()


def test_recovered_promotions_are_reported(tmp_path: Path, monkeypatch):
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(install, "recover_interrupted_promotions", lambda _root: ["restored backup -> target"])
    monkeypatch.setattr(install, "clone_or_pull", lambda *a, **k: InstallResult(True, "nothing to do"))
    install_or_update(entry(), tmp_path, progress=lambda phase, message: seen.append((phase, message)))
    assert any("restored backup -> target" in message for _phase, message in seen)
    evidence = (tmp_path / EVIDENCE_DIRECTORY / EVIDENCE_FILE).read_text(encoding="utf-8")
    assert "restored backup -> target" in evidence


# --- one install or update at a time per workspace --------------------------

def test_the_workspace_lock_is_exclusive_and_released(tmp_path: Path):
    first = WorkspaceLock(tmp_path)
    first.acquire()
    try:
        with pytest.raises(WorkspaceBusyError):
            WorkspaceLock(tmp_path).acquire()
    finally:
        first.release()
    again = WorkspaceLock(tmp_path)
    again.acquire()
    again.release()


def test_an_update_refuses_to_start_while_another_one_holds_the_workspace(tmp_path: Path):
    holder = WorkspaceLock(tmp_path)
    holder.acquire()
    try:
        results = install_or_update(entry(), tmp_path)
    finally:
        holder.release()
    assert [r.ok for r in results] == [False]
    assert "already running" in results[0].message


# --- the signature gate also covers a first install -------------------------

def test_an_unsigned_first_install_is_refused_before_anything_is_built(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_release(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv(install.REQUIRE_SIGNED_ENV, "1")

    results = install_or_update(entry(), workspace)

    assert [r.ok for r in results] == [False]
    assert "no valid signature" in results[0].message
    assert not (workspace / entry().name).exists()
    assert not list(workspace.glob(".*.clone-*")), "the staging clone must be removed"


def test_a_signed_first_install_goes_through(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_release(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv(install.REQUIRE_SIGNED_ENV, "1")
    monkeypatch.setattr(install, "verify_candidate_signature", lambda _path: (True, "Good signature"))

    results = install_or_update(entry(), workspace)

    assert all(r.ok for r in results), [r.message for r in results]
    assert (workspace / entry().name / "built.txt").exists()


def test_a_fresh_install_whose_build_fails_is_not_left_half_installed(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_release(tmp_path, build_ok=False)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))

    results = install_or_update(entry(), workspace)

    assert not all(r.ok for r in results)
    assert not (workspace / entry().name).exists()


def test_signature_can_be_required_by_the_saved_settings():
    assert install.signature_required() is False
    settings.save_require_signed_commits(True)
    assert install.signature_required() is True


def test_a_damaged_settings_file_fails_closed(isolated_settings: Path):
    isolated_settings.write_text("{ this is not json", encoding="utf-8")
    assert settings.settings_file_is_damaged() is True
    assert install.signature_required() is True


def test_a_missing_settings_file_does_not_require_signatures(isolated_settings: Path):
    assert not isolated_settings.exists()
    assert install.signature_required() is False


# --- the installed checkout is never left in a broken state -----------------

def test_a_blocked_first_rename_leaves_the_installation_untouched(tmp_path: Path, monkeypatch):
    local, old_head = _two_commit_checkout(tmp_path)
    real_rename = Path.rename

    def blocked(self: Path, target):
        if self == local:
            raise PermissionError("[WinError 32] the file is being used by another process")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", blocked)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "close every program" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == old_head
    assert not list(tmp_path.glob(f".{entry().name}.update-*")), "the staging clone must be removed"
    assert not list(tmp_path.glob(f"{entry().name}.backup-*"))


def test_local_commits_are_named_in_the_refusal(tmp_path: Path):
    local, _old = _two_commit_checkout(tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=local)
    git("config", "user.name", "Contract", cwd=local)
    (local / "local-only.txt").write_text("mine\n", encoding="utf-8")
    git("add", "local-only.txt", cwd=local)
    git("commit", "-m", "a local fix nobody else has", cwd=local)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "local commit" in result.message
    assert "a local fix nobody else has" in result.message
    assert not list(tmp_path.glob(f".{entry().name}.update-*")), "no staging clone is even needed"


def test_a_file_that_cannot_be_carried_over_stops_the_update_cleanly(tmp_path: Path, monkeypatch):
    local, old_head = _two_commit_checkout(tmp_path)
    (local / "settings.local").write_text("keep me\n", encoding="utf-8")

    def refuse(*_args, **_kwargs):
        raise PermissionError("root owns this file")

    monkeypatch.setattr(install, "copy2", refuse)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "settings.local" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == old_head
    assert not list(tmp_path.glob(f".{entry().name}.update-*"))


def test_build_output_is_not_carried_over_at_any_depth(tmp_path: Path):
    local, _old = _two_commit_checkout(tmp_path)
    (local / ".gitignore").write_text("node_modules/\n.venv/\n__pycache__/\n", encoding="utf-8")
    git("add", ".gitignore", cwd=local)
    for rel in ("web/node_modules/pkg/index.js", "clients/python/.venv/pyvenv.cfg", "src/x/__pycache__/m.pyc", "data/state.db"):
        target = local / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    staging = tmp_path / "staging"
    staging.mkdir()

    install._carry_over_local_data(local, staging)

    assert (staging / "data" / "state.db").exists()
    assert not (staging / "web").exists()
    assert not (staging / "clients").exists()
    assert not (staging / "src").exists()


# --- cleanup of leftovers ---------------------------------------------------

def test_read_only_git_files_do_not_block_the_cleanup(tmp_path: Path):
    staging = tmp_path / f".{entry().name}.update-abc"
    pack = staging / ".git" / "objects" / "pack"
    pack.mkdir(parents=True)
    file = pack / "pack-1.idx"
    file.write_text("x", encoding="utf-8")
    os.chmod(file, stat.S_IREAD)
    if os.name != "nt":
        os.chmod(pack, stat.S_IREAD | stat.S_IEXEC)

    install._rmtree_best_effort(staging)

    assert not staging.exists()


def test_old_staging_directories_are_removed_and_recent_ones_are_kept(tmp_path: Path):
    old = tmp_path / ".HYDRA-UMC-X.update-old"
    recent = tmp_path / ".HYDRA-UMC-X.clone-recent"
    real = tmp_path / "HYDRA-UMC-X"
    for folder in (old, recent, real):
        folder.mkdir()
        (folder / "f.txt").write_text("x", encoding="utf-8")
    long_ago = time.time() - 3 * 60 * 60
    os.utime(old, (long_ago, long_ago))
    os.utime(real, (long_ago, long_ago))

    removed = cleanup_orphaned_staging(tmp_path)

    assert removed == [old]
    assert recent.exists() and real.exists()


def test_prune_keeps_the_newest_backups_of_every_project(tmp_path: Path):
    now = time.time()
    names = {
        "HYDRA-UMC-A.backup-aaaaaaa1": now - 400,
        "HYDRA-UMC-A.backup-aaaaaaa2": now - 300,
        "HYDRA-UMC-A.backup-aaaaaaa3": now - 100,
        "HYDRA-UMC-B.backup-bbbbbbb1": now - 200,
    }
    for name, stamp in names.items():
        folder = tmp_path / name
        folder.mkdir()
        os.utime(folder, (stamp, stamp))
    (tmp_path / "HYDRA-UMC-A").mkdir()

    assert {removed.name for removed in prune_backups(tmp_path, keep=2, dry_run=True)} == {"HYDRA-UMC-A.backup-aaaaaaa1"}
    assert (tmp_path / "HYDRA-UMC-A.backup-aaaaaaa1").exists(), "a dry run removes nothing"

    prune_backups(tmp_path, keep=2)

    assert not (tmp_path / "HYDRA-UMC-A.backup-aaaaaaa1").exists()
    assert (tmp_path / "HYDRA-UMC-A.backup-aaaaaaa2").exists()
    assert (tmp_path / "HYDRA-UMC-A.backup-aaaaaaa3").exists()
    assert (tmp_path / "HYDRA-UMC-B.backup-bbbbbbb1").exists()
    assert (tmp_path / "HYDRA-UMC-A").exists(), "the installation itself is never a backup"
    assert set(list_backups(tmp_path)) == {"HYDRA-UMC-A", "HYDRA-UMC-B"}


def test_the_prune_command_reports_what_it_did(tmp_path: Path, capsys):
    for suffix in ("1", "2", "3"):
        (tmp_path / f"HYDRA-UMC-A.backup-0000000{suffix}").mkdir()
    args = main_module.build_parser().parse_args(["prune-backups", "--workspace", str(tmp_path), "--keep", "1", "--dry-run"])
    assert args.func(args) == 0
    assert "2 of 3 backup(s) would be removed" in capsys.readouterr().out


# --- order of a batch -------------------------------------------------------

def test_a_batch_installs_the_sdk_first_and_the_updater_last():
    names = ["HYDRA-UMC-UPDATER", "HYDRA-UMC-STUDIO", "HYDRA-UMC-SDK", "HYDRA-UMC-AAA"]
    assert sorted(names, key=batch_order_key) == [
        "HYDRA-UMC-SDK", "HYDRA-UMC-AAA", "HYDRA-UMC-STUDIO", "HYDRA-UMC-UPDATER",
    ]


# --- the default workspace --------------------------------------------------

def test_the_workspace_variable_wins(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(main_module.WORKSPACE_ENV, str(tmp_path))
    assert main_module.default_workspace_root() == tmp_path.resolve()


def test_an_installed_copy_never_uses_its_own_environment_as_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(main_module.WORKSPACE_ENV, raising=False)
    fake = tmp_path / ".venv" / "lib" / "site-packages" / "hydra_umc_updater" / "main.py"
    assert main_module._installed_as_package(fake)
    assert not main_module._installed_as_package(tmp_path / "GitHub" / "HYDRA-UMC-UPDATER" / "src" / "hydra_umc_updater" / "main.py")


# --- a discovered project keeps its own default branch ----------------------

def test_a_project_is_read_from_its_own_default_branch():
    on_trunk = ProjectEntry("HYDRA-UMC-X", "python", "pyproject.toml", r"(\d+)", branch="trunk")
    assert "/HYDRA-UMC-X/trunk/" in github_raw_url(on_trunk)
    assert "/HYDRA-UMC-EXAMPLE/main/" in github_raw_url(entry())
