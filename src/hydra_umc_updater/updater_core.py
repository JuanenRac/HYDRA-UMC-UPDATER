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
all of them. `EcosystemProfile` lives in `updater_profile.py`, the one file that is the same in every updater; this updater uses the HYDRA-UMC profile; `docs/UPDATER_CORE.md` lists
which modules already read the profile and which are the next to move."""
from __future__ import annotations

from .project_manifest import ECOSYSTEM_ID, MANIFEST_FILE
from .updater_profile import EcosystemProfile, profile_in

__all__ = ["COMMON_REPO", "EcosystemProfile", "HYDRA_PROFILE", "PROFILES", "profile_for", "CORE_MODULES"]


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

#: The shared contracts repository of the family: the one a manifest's `min_common` is compared with.
COMMON_REPO = "HYDRA-UMC-SDK"

#: the profiles this updater knows. The other families register theirs when their updater adopts the core.
PROFILES: dict[str, EcosystemProfile] = {HYDRA_PROFILE.ecosystem_id: HYDRA_PROFILE}


def profile_for(ecosystem_id: str) -> EcosystemProfile:
    """The profile of `ecosystem_id`; an unknown family is an error, never a silent fallback to another one."""
    return profile_in(PROFILES, ecosystem_id)


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
