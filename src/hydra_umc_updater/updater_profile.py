# =============================================================================
# Updater profile - the names that differ between the updaters of the families
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The part of the common core that is the same file in every updater.

This file is copied, byte for byte, into the HYDRA-UMC, URTC and A.R.M.O.R. updaters (and into any
other updater that adopts the core). It imports nothing from the package it lives in, so the copies
cannot differ in anything but their bytes; a test in each updater pins the digest of the file and
compares it with the copies next to it when they are present. To change it, change all the copies
in one go and update the digest in the three tests.

`EcosystemProfile` holds the handful of names a family gives to what the updater keeps and reads:
the ecosystem id the manifests carry, the manifest file, the prefix of the environment variables,
the hidden files and folders, the User-Agent, the prefix of the repositories and the order of a
batch. Each updater has its own `updater_core.py` with the profile of its family."""
from __future__ import annotations

import os
from dataclasses import dataclass


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

    def thread_prefix(self, role: str) -> str:
        """The name worker threads of `role` carry, for example `hydra-umc-github`."""
        return f"{self.user_agent.removesuffix('-UPDATER').lower()}-{role}"


def profile_in(profiles: dict[str, EcosystemProfile], ecosystem_id: str) -> EcosystemProfile:
    """The profile of `ecosystem_id` among `profiles`; an unknown family is an error, never a silent fallback to another one."""
    try:
        return profiles[ecosystem_id]
    except KeyError:
        raise KeyError(f"no updater profile for the ecosystem {ecosystem_id!r}") from None
