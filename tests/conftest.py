# =============================================================================
# HYDRA-UMC-UPDATER - Shared test fixtures
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

from pathlib import Path

import pytest

from hydra_umc_updater import settings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keeps every test away from the real settings file of whoever runs it, so a
    saved language, workspace or signature requirement never changes a result."""
    path = tmp_path_factory.mktemp("settings") / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    monkeypatch.delenv("HYDRA_UMC_UPDATER_REQUIRE_SIGNED", raising=False)
    # no test writes the ETag cache of whoever runs it
    monkeypatch.setenv("HYDRA_UMC_UPDATER_NO_CACHE", "1")
    return path
