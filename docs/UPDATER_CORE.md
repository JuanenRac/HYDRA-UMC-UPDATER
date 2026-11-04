# The common core of the updaters

The updaters of the families (HYDRA-UMC, URTC, A.R.M.O.R. and Electro Hobby 3D) do the same work: find the
projects, compare versions, bring a checkout in a staging folder, verify it, build it, promote it and leave
a trace. What differs is a handful of names. This updater keeps those names in one place, so the rest of the
code can serve another family without a copy and a fix written once reaches all of them.

## The profile

`updater_core.EcosystemProfile` holds what differs:

| Field | Meaning | HYDRA-UMC |
|---|---|---|
| `ecosystem_id` | The id the manifests carry in `ecosystem` | `HYDRA-UMC` |
| `manifest_file` | The manifest at the root of every repository | `hydra-umc.project.json` |
| `env_prefix` | The prefix of the environment variables | `HYDRA_UMC_UPDATER` |
| `state_directory` | The folder, inside the workspace, for the files the updater writes | `.hydra-umc-updater` |
| `user_agent` | The name sent to GitHub and used for worker threads | `HYDRA-UMC-UPDATER` |
| `repo_prefix` | The prefix every repository of the family carries | `HYDRA-UMC` |
| `file_prefix` | The prefix of the hidden files in the home directory and the workspace | `.hydra_umc_updater` |
| `trains_directory` | The folder, inside the workspace, of the version trains | `.hydra-umc-trains` |
| `batch_first`, `batch_last` | The projects that go first and last in a batch | `HYDRA-UMC-SDK`, `HYDRA-UMC-UPDATER` |

`profile_for(id)` refuses an unknown family; it never falls back to another one.

## Which modules read the profile

`CORE_MODULES` lists the modules of the core and whether they already read the profile:

| Module | Reads the profile |
|---|---|
| `evidence`, `evidence_export`, `deploy_plan` | yes |
| `project_manifest` | yes (`parse_manifest(..., ecosystem_id=...)`) |
| `github_client`, `install`, `train`, `settings` | yes (user agent, environment variables, hidden files, manifest file, repository names) |

## What each other updater has to do (not done here)

The other updaters live in other repositories and are not touched from this one. To adopt the core, each one:

1. registers its profile in `PROFILES`;
2. points its copy of `github_client`, `install`, `train` and `settings` at its own profile (the modules of this updater already read it) and sets the same flags in `CORE_MODULES`;
3. keeps its own manifest fields in its own parser and shares the verification, the lock, the staging flow and
   the rollback.

The core becomes its own package only when two updaters have adopted the profile; until then it is copied and
kept in step, one file at a time, so nobody depends on a package that does not exist yet.

## Pending ports

`image verify` (`image_release.py`, the check of the signed image releases of the image builder) exists only in this updater
so far. The updaters of the other families and the general updater still have to take it: the module has no names of this
family except the environment prefix, which it reads from the profile through the command.

`release_channel.py` and `package_release.py` (the latest stable release instead of the head, and the signed package of a release) also exist only in
this updater so far; they read the pinned key of the releases and the settings, and have no names of this family except the prefix of the signed text.
