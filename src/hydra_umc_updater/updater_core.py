# =============================================================================
# HYDRA-UMC-UPDATER - Common core seam: updater_core.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""What differs between the updaters of the families, in one place.

The installer, the GitHub client, the manifest parser, the evidence file and the
version trains are the same program for every family; only a handful of names
change (the ecosystem id the manifests carry, the manifest file, the prefix of the
environment variables, the folder of the evidence file). An `EcosystemProfile`
holds those names, so a module that takes a profile serves another family without
a copy, and a fix (a lock, a signature check, a safe removal) written once reaches
all of them. This updater uses the HYDRA-UMC profile; `docs/UPDATER_CORE.md` lists
which modules already read the profile and which are the next to move."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .project_manifest import ECOSYSTEM_ID, MANIFEST_FILE


@dataclass(frozen=True)
class EcosystemProfile:
    #: the id the manifests of the family carry in their `ecosystem` field
    ecosystem_id: str
    #: the file name of the manifest at the root of every repository
    manifest_file: str
    #: the prefix of the environment variables of the updater (`<PREFIX>_OS_DEPLOY`...)
    env_prefix: str
    #: the folder, inside the workspace, that holds the files the updater writes about its own work
    state_directory: str
    #: the name the updater sends as User-Agent and prefixes its worker threads with (lower-case for threads)
    user_agent: str
    #: the prefix every repository of the family carries (`<prefix>` or `<prefix>-<NAME>`)
    repo_prefix: str
    #: the prefix of the hidden files the updater keeps in the home directory and the workspace (`<prefix>_settings.json`...)
    file_prefix: str
    #: the folder, inside the workspace, of the version trains
    trains_directory: str
    #: the projects that go first and last in a batch (the shared library and the updater itself)
    batch_first: tuple[str, ...]
    batch_last: tuple[str, ...]

    def env_name(self, suffix: str) -> str:
        """The environment variable of this family for `suffix`, for example `OS_DEPLOY`."""
        return f"{self.env_prefix}_{suffix}"

    def env_text(self, suffix: str) -> str:
        return os.environ.get(self.env_name(suffix), "").strip()

    def env_flag(self, suffix: str) -> bool | None:
        """True or False when the variable says so, None when it is unset or means nothing."""
        value = self.env_text(suffix).lower()
        if value in {"1", "true", "yes", "on"}:
            return True
        if value in {"0", "false", "no", "off"}:
            return False
        return None


HYDRA_PROFILE = EcosystemProfile(
    ecosystem_id=ECOSYSTEM_ID,
    manifest_file=MANIFEST_FILE,
    env_prefix="HYDRA_UMC_UPDATER",
    state_directory=".hydra-umc-updater",
    user_agent="HYDRA-UMC-UPDATER",
    repo_prefix="HYDRA-UMC",
    file_prefix=".hydra_umc_updater",
    trains_directory=".hydra-umc-trains",
    batch_first=("HYDRA-UMC-SDK",),
    batch_last=("HYDRA-UMC-UPDATER",),
)

#: the profiles this updater knows. The other families register theirs when their updater adopts the core.
PROFILES: dict[str, EcosystemProfile] = {HYDRA_PROFILE.ecosystem_id: HYDRA_PROFILE}


def profile_for(ecosystem_id: str) -> EcosystemProfile:
    """The profile of `ecosystem_id`; an unknown family is an error, never a silent fallback to another one."""
    try:
        return PROFILES[ecosystem_id]
    except KeyError:
        raise KeyError(f"no updater profile for the ecosystem {ecosystem_id!r}") from None


#: The modules that make the core, and whether they already read the profile (True) or still hold names of this family (False).
CORE_MODULES: dict[str, bool] = {
    "evidence": True,
    "evidence_export": True,
    "deploy_plan": True,
    "project_manifest": True,
    "github_client": True,
    "install": True,
    "train": True,
    "settings": True,
}
