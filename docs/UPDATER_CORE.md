# The common core of the updaters

The updaters of the families (HYDRA-UMC, URTC, A.R.M.O.R. and Electro Hobby 3D) do the same work: find the
projects, compare versions, bring a checkout in a staging folder, verify it, build it, promote it and leave
a trace. What differs is a handful of names. This updater keeps those names in one place, so the rest of the
code can serve another family without a copy and a fix written once reaches all of them.

## The profile

`EcosystemProfile` (defined in `updater_profile.py`, re-exported by `updater_core`) holds what differs:

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

## The file that is the same in every updater

`updater_profile.py` (the class `EcosystemProfile` and the helpers that build names from it) is copied byte for byte into the URTC and A.R.M.O.R. updaters, which have taken the profile for their user agent, environment variables, hidden files, state folder and manifest file. `tests/test_updater_profile_copy.py` pins its digest and compares the copies when the other updaters are next to this repository; to change it, change the three copies and the digest in the three tests. The other modules are not merged: they differ in the behaviour that belongs to each family.

## What each other updater has to do

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

## The manifest contract

Every updater of the families reads the same set of manifest fields, whatever the family. This is the least they share, and `tests/test_manifest_contract.py` (the same test in each updater) pins it:

| Part | Fields |
|---|---|
| Required in every manifest | `schema_version`, `ecosystem`, `name`, `version`, `role`, `stack`, `technologies`, `deployment_target`, `maturity`, `family`, `parent`, `native_version`, `build`, `notes` |
| Optional, accepted by every updater | `service`, `deployment_target_note`, `evidence`, `hardware_bound`, `min_common` |
| Attributes of the reader's result | the required fields (the native version as one value or as a file and a pattern, depending on the family), `service_port`, `service_health_path`, `service_systemd_unit` and `min_common` |

What is not part of the contract is allowed to differ and is kept apart: the value rules of a family (for example the free-text role of one family against the closed list of another) and the fields that belong to one family only (`depends_on`, `requires`, `components`, `binary`...). A misspelled field is refused as unknown in every updater. When the updaters sit next to one another, the test compares their readers; the reader of the updater of Electro Hobby 3D is read from its main branch with git, read only.

Two files are the same in every updater and are pinned by a digest in the tests: `updater_profile.py` (the names of the family) and `common_gate.py` (the reading of `min_common`, below).

## `min_common` in the manifest

A manifest may carry the optional field `min_common`: the oldest version of the shared contracts repository (HYDRA-UMC-SDK) the project works with (three or four numbers). The updater accepts it and reads it into `ProjectManifest.min_common` and `ProjectEntry.min_common`; a value that is not a version is ignored (`None`) and never refuses the manifest, so a project that says it cannot stop an updater that does not understand it. A misspelled name of the field is still refused as an unknown field.

### What the updater does with it

`status` compares the `min_common` of every project with the version of HYDRA-UMC-SDK installed in the workspace and, when a project asks for a newer one, prints a warning on the error stream (and lists it under `common_notices` in the `--json` output). It only warns: no update is held back and nothing is refused. When HYDRA-UMC-SDK is not installed or its version cannot be read, a project that asks for a minimum gets a notice that says the installed version is not known.

| Setting | Environment variable | Values |
|---|---|---|
| `min_common_check` in `~/.hydra_umc_updater_settings.json` | `HYDRA_UMC_UPDATER_MIN_COMMON` | `warn` (the default) or `off`. Anything else counts as the default, so a typo never silences the notice. The environment variable wins over the saved setting. |

The comparison counts the fourth number (a missing one is 0). There is no value that holds an update back: whether the installed contracts may stop an update is a decision for later, and this reading is what it would be built on.

### Publication

No manifest of the projects carries `min_common` yet. It is published in the manifests and in the shared manifest schema once every updater of the families reads it.
