# =============================================================================
# HYDRA-UMC-UPDATER - names and texts outside ASCII in what git writes
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Real local git repositories, no network. On Windows the console code page is not UTF-8, which is where these used to fail."""
from __future__ import annotations

import json

from hydra_umc_updater.install import _manifest_from_revision, _real_untracked_paths, clone_or_pull
from train_helpers import git

NAME = "HYDRA-UMC-DATALAKE"
KEPT = {"configuración.json": "{}", "datos/mediciones_ñ.csv": "1;2", "ログ.txt": "x"}


def test_local_files_with_names_outside_ascii_survive_an_update(world):
    repo = world.make(NAME, "1.0.0")
    entry = world.entries(NAME)[NAME]
    assert clone_or_pull(entry, world.workspace).ok
    local = world.workspace / NAME
    for name, content in KEPT.items():
        target = local / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    assert any("configuración.json" == path for path in _real_untracked_paths(local))
    repo.publish("1.1.0")
    result = clone_or_pull(entry, world.workspace)
    assert result.ok, result.message
    assert json.loads((local / "hydra-umc.project.json").read_text(encoding="utf-8"))["version"] == "1.1.0"
    for name, content in KEPT.items():
        assert (local / name).read_text(encoding="utf-8") == content, name


def test_a_manifest_with_text_outside_ascii_is_read_from_git(world):
    repo = world.make(NAME, "1.0.0")
    manifest = repo.seed / "hydra-umc.project.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["notes"] = "Notas: señal, Ü, 日本語の説明, 中文说明, ”quoted” – ok"  # bytes that cp1252 has no character for
    manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    git("commit", "-q", "-am", "notas con señal ”日本”", cwd=repo.seed)
    read = _manifest_from_revision(repo.seed, "HEAD", world.entries(NAME)[NAME])
    assert read.version == "1.0.0"
