# =============================================================================
# HYDRA-UMC-UPDATER - Safe install/update behavior tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from hydra_umc_updater import install
from hydra_umc_updater.install import clone_or_pull, find_build_test_script, run_build_script
from hydra_umc_updater.registry import ProjectEntry


def entry() -> ProjectEntry:
    return ProjectEntry("HYDRA-UMC-EXAMPLE", "python", "pyproject.toml", r"(\d+)\.(\d+)\.(\d+)")


def test_prefers_the_non_versioning_build_test_script(tmp_path: Path):
    project = tmp_path / entry().name
    project.mkdir()
    expected = project / ("build-test.bat" if os.name == "nt" else "build-test.sh")
    expected.write_text("build test\n", encoding="utf-8")
    (project / "build.sh").write_text("versioned build\n", encoding="utf-8")

    assert find_build_test_script(project) == expected


def test_never_touches_an_existing_non_git_directory(tmp_path: Path):
    project = tmp_path / entry().name
    project.mkdir()
    sentinel = project / "operator-file.txt"
    sentinel.write_text("must remain untouched", encoding="utf-8")

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "isn't a git checkout" in result.message
    assert sentinel.read_text(encoding="utf-8") == "must remain untouched"


def test_missing_build_test_fails_closed(tmp_path: Path):
    project = tmp_path / entry().name
    project.mkdir()

    assert find_build_test_script(project) is None


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def write_manifest(path: Path, version: str) -> None:
    (path / "hydra-umc.project.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "ecosystem": "HYDRA-UMC",
                "name": entry().name,
                "version": version,
                "role": "service",
                "stack": "python",
                "technologies": ["Python"],
                "deployment_target": "cm5",
                "maturity": "functional",
                "family": "Test",
                "parent": None,
                "native_version": {"file": "pyproject.toml", "pattern": "(\\d+)\\.(\\d+)\\.(\\d+)"},
                "build": "python -m compileall src",
                "notes": "Test manifest.",
            }
        ),
        encoding="utf-8",
    )


def test_failed_clone_removes_only_its_staging_directory(tmp_path: Path, monkeypatch):
    missing_remote = tmp_path / "does-not-exist.git"
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(missing_remote))

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert not (tmp_path / entry().name).exists()
    assert not list(tmp_path.glob(f".{entry().name}.clone-*"))


def test_diverged_pull_fails_without_resetting_local_checkout(tmp_path: Path):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    (seed / "state.txt").write_text("base\n", encoding="utf-8")
    write_manifest(seed, "1.0.0")
    git("add", "state.txt", "hydra-umc.project.json", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=local)
    git("config", "user.name", "Contract", cwd=local)
    (local / "state.txt").write_text("local\n", encoding="utf-8")
    git("commit", "-am", "local", cwd=local)
    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()

    (seed / "state.txt").write_text("remote\n", encoding="utf-8")
    git("commit", "-am", "remote", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "merge --ff-only failed" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == local_head
    assert (local / "state.txt").read_text(encoding="utf-8") == "local\n"


def write_build_script(path: Path, *, ok: bool) -> None:
    """Writes both build-test.sh and build-test.bat (whichever
    find_build_test_script actually picks for the current OS is the one
    that matters) - `ok` controls whether it succeeds or fails, and a
    successful run also drops a real marker file (built.txt) so a test
    can confirm the STAGING build's own artifacts - not just its source -
    made it into the promoted checkout (UPD-01)."""
    if ok:
        (path / "build-test.sh").write_text("#!/usr/bin/env bash\necho built > built.txt\nexit 0\n", encoding="utf-8")
        (path / "build-test.bat").write_text("@echo off\r\necho built> built.txt\r\nexit /b 0\r\n", encoding="utf-8")
    else:
        (path / "build-test.sh").write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        (path / "build-test.bat").write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")


def test_update_verifies_build_in_staging_before_promoting_and_keeps_a_backup(tmp_path: Path):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    old_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()

    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "new release", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    new_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=seed, text=True).strip()

    result = clone_or_pull(entry(), tmp_path)

    assert result.ok, result.message
    assert "previous installation kept at" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == new_head
    # The promoted checkout must have the STAGING build's own real
    # artifact, not a second, separate build - proving the fix promotes
    # the same directory it verified, rather than rebuilding blind.
    assert (local / "built.txt").exists()

    backup = tmp_path / f"{entry().name}.backup"
    assert backup.is_dir()
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=backup, text=True).strip() == old_head

    # No leftover staging directories from a successful run.
    assert not list(tmp_path.glob(f".{entry().name}.update-*"))


def test_update_restores_the_real_upstream_remote_on_the_promoted_checkout(tmp_path: Path, monkeypatch):
    # REV-001 (found in an independent revalidation audit, P1): the
    # staging clone `git clone --local ...` creates is a clone OF the
    # local installation path, so its own `origin` remote used to end up
    # pointing at that local path - never this project's real upstream -
    # once promoted, permanently stopping this checkout from ever
    # discovering a real future update again.
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    # This test's own real upstream IS the bare repo above - matches how
    # a real deployment's github_repo_url() always names the SAME real
    # remote the checkout was originally cloned from.
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))

    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "new release", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert result.ok, result.message
    restored_origin = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=local, text=True).strip()
    assert restored_origin == str(remote), (
        f"origin must be the real upstream {remote}, not the local install path (or anything else) - got {restored_origin!r}"
    )


def test_update_carries_over_real_local_data_never_tracked_by_git(tmp_path: Path):
    # REV-002 (found in an independent revalidation audit, P1): `git
    # clone --local` only ever copies the committed object database - a
    # project's own real local data (config, accounts, generated
    # certificates, ...) living untracked inside its checkout used to be
    # left behind entirely once the old installation was renamed aside.
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    (seed / ".gitignore").write_text("data/\n", encoding="utf-8")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    # A real, genuinely untracked file (never added/committed at all) -
    # the audit's own exact reproduction shape.
    (local / "audit-local-settings.txt").write_text("real operator configuration\n", encoding="utf-8")
    # A real, gitignored directory with real data inside it - the shape
    # every server-side project in this ecosystem actually uses
    # (data/settings.json, data/users.json, ...).
    (local / "data").mkdir()
    (local / "data" / "settings.json").write_text('{"real": "operator settings"}', encoding="utf-8")
    # A real, untracked build-artifact-like directory - must NEVER be
    # carried over even though git also considers it untracked.
    (local / "node_modules").mkdir()
    (local / "node_modules" / "some-package.js").write_text("// not real project source\n", encoding="utf-8")

    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "new release", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert result.ok, result.message
    assert (local / "audit-local-settings.txt").read_text(encoding="utf-8") == "real operator configuration\n"
    assert (local / "data" / "settings.json").read_text(encoding="utf-8") == '{"real": "operator settings"}'
    assert not (local / "node_modules").exists(), "a build-artifact-like directory must never be carried over"


def test_update_refuses_when_a_real_tracked_file_has_an_uncommitted_edit(tmp_path: Path):
    # V07-001 (found in an independent revalidation audit, P1, a real
    # gap this module's own docstring did not actually close once UPD-01
    # switched to the staging-clone flow): `git clone --local` only ever
    # copies the COMMITTED object database - a genuinely dirty edit to a
    # TRACKED file lives only in the installed checkout's own working
    # tree, so the staging clone never sees it at all, and
    # _carry_over_local_data() deliberately never carries over a tracked
    # file (only real `??`/`!!` untracked/ignored paths - see its own
    # docstring). The staging clone's own `git merge --ff-only` therefore
    # always succeeds (its working tree starts clean), the build
    # succeeds, and promotion renames the dirty original aside to
    # `.backup` - the edit survives only there, never in the newly active
    # checkout, while clone_or_pull() still reports ok=True. This
    # directly contradicts this module's own documented promise ("a real
    # local edit... fails loudly... instead of being silently
    # discarded"), which was only ever true for the older,
    # verify_build=False in-place-merge path.
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    (seed / "tracked.txt").write_text("committed\n", encoding="utf-8")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    # A real, uncommitted edit to an already-TRACKED file - never staged,
    # never committed, exactly the audit's own reproduction shape.
    (local / "tracked.txt").write_text("USER_UNCOMMITTED\n", encoding="utf-8")

    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "new release", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok, (
        "an update must refuse when a real tracked file has an uncommitted edit, "
        f"not silently discard it while reporting ok=True (got: {result.message!r})"
    )
    assert "uncommitted" in result.message.lower() or "dirty" in result.message.lower()
    # The refusal must happen before anything is touched - the real edit
    # must still be sitting in the ORIGINAL checkout's own working tree,
    # never moved aside to .backup.
    assert (local / "tracked.txt").read_text(encoding="utf-8") == "USER_UNCOMMITTED\n"
    assert not (tmp_path / f"{entry().name}.backup").exists(), "a refused update must never rename anything aside"


def test_update_build_failure_leaves_the_previous_installation_completely_untouched(tmp_path: Path):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    old_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()

    # UPD-01's own exact reproduction: the candidate's manifest is real
    # and newer, but its build is broken.
    write_manifest(seed, "1.1.0")
    write_build_script(seed, ok=False)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "broken release", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "left completely untouched and remains the operative installation" in result.message
    # The real closure criterion: the previous installation is still
    # exactly where it was, on its previous revision, still buildable.
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == old_head
    assert not (local / "built.txt").exists()
    build_result = run_build_script(entry(), tmp_path)
    assert build_result.ok, "the untouched previous installation must still build successfully"

    assert not (tmp_path / f"{entry().name}.backup").exists()
    assert not list(tmp_path.glob(f".{entry().name}.update-*"))


def test_update_without_verify_build_restores_the_old_in_place_merge_behavior(tmp_path: Path):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "base", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)

    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "new release", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    new_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=seed, text=True).strip()

    result = clone_or_pull(entry(), tmp_path, verify_build=False)

    assert result.ok, result.message
    assert "Pulled latest into" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == new_head
    # No staging clone, no backup - verify_build=False is the plain,
    # pre-existing in-place merge, unchanged.
    assert not (tmp_path / f"{entry().name}.backup").exists()
    assert not list(tmp_path.glob(f".{entry().name}.update-*"))


def test_refuses_a_remote_manifest_version_lower_than_the_installed_version(tmp_path: Path):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "2.0.0")
    git("add", "hydra-umc.project.json", cwd=seed)
    git("commit", "-m", "initial", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()

    write_manifest(seed, "1.9.9")
    git("add", "hydra-umc.project.json", cwd=seed)
    git("commit", "-m", "bad downgrade", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    result = clone_or_pull(entry(), tmp_path)

    assert not result.ok
    assert "anti-rollback refused update" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == local_head
