# Security Policy 🔒 (HYDRA-UMC-UPDATER)

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x.x   | ✅ Yes    |

## Reporting a Vulnerability

**CRITICAL: Do not report vulnerabilities through public GitHub issues.**

This tool clones and executes each ecosystem project's own build script
(`install.py`) and fetches version files over the network from GitHub
(`github_client.py`) - both are real, meaningful attack surfaces for a
tool that runs on the CM5 with the same privileges as everything else on
it. If you discover a vulnerability affecting:

- **What gets executed** - a way to make `install`/`update` run something
  other than the target project's own real build script.
- **Where a clone/pull lands** - a path-traversal or similar issue in how
  a project name maps to a filesystem path under the workspace root.
- **What version data is trusted** - a way to make the GitHub version
  check report a false "up to date"/"outdated" state that could mislead
  someone into skipping a real update, or attempting one that isn't
  actually needed.
- **The signature gate** - a way to run a project's `build-test` script
  from a commit that fails `git verify-commit` while the requirement
  (`HYDRA_UMC_UPDATER_REQUIRE_SIGNED=1`, or `require_signed_commits` in
  the saved settings) is on. The gate covers a first install and an
  update. It is off by default and only as strong as the keyring or ssh
  allowed-signers file of the machine it runs on; a damaged settings file
  is read as "required". With the gate off, the `build-test` script of the
  commit being installed runs with this user's privileges before anything
  has shown who published it - the window says so while that is the case.

please report it responsibly:

1. **Email**: Send a detailed report to `electrohobby3d@gmail.com`.
2. **Impact**: Describe the attack surface affected and a realistic
   scenario (this tool has no network-facing service of its own - it's a
   CLI a person runs by hand, so most realistic scenarios involve a
   compromised/typosquatted upstream repo, not a remote attacker directly
   reaching this tool).
3. **Response**: Initial acknowledgment within 48 hours.

We follow a coordinated disclosure policy.
