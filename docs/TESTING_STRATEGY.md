# Testing strategy: property-based tests and mutation checks of the signed package of a release

The updater installs a package only after it has checked its name, its hash, its Ed25519 signature by the pinned key of the releases and its members. That check (`package_release.py`) is tested with property-based tests besides the hand-written cases.

## Property-based tests

`tests/test_property_package_release.py` states rules that must hold for every input and checks them on generated cases. The cases come from a small generator with a fixed seed (`random.Random`), so a run is the same on every machine, nothing extra is installed to run it, and the whole file takes about ten seconds. The rules:

| Area | Rule checked on generated inputs |
| --- | --- |
| Signature | any change to the signature (one nibble, a cut, an extension, random hexadecimal, empty) is refused, even when the person allows unsigned packages; a signature is bound to the project, the version and the hash, so a signed package of another project or of another version is refused; a signature of another key is refused |
| Hash | a changed package is refused whatever else the attacker changes: with the old hash (`sha256_bad`), and with a rewritten hash the old signature no longer matches (`sig_bad`); a missing or malformed `.sha256` is refused; the hash is read in upper case too |
| Members | a link (symbolic or hard), a device, a pipe, a path with `..`, an absolute path, a back-slash, a drive letter or a `.git` member is refused, and nothing is written, not even a staging folder; the extraction refuses a path outside its folder on its own |
| Names | a package not named `<project>-<version>.tgz` is refused |
| Unsigned | an unsigned package is accepted only when the person allowed it, and the environment variable can only turn the requirement on |
| Version | the manifest inside the package must say the version of the package; a version that is not newer than the installed one is refused; a newer one keeps the previous folder as a backup, never deleted |
| Key | a pinned key that is not 64 lower-case hexadecimal characters is refused |

## Mutation checks (local only)

Mutation testing changes the code of a module in small ways (a `<` for a `<=`, a constant, a condition) and runs the tests: a change the tests do not notice is a behaviour nobody checks. It is a measure of the tests, not a part of the build: it is **not** run in the CI, and a run takes several minutes. To repeat it, in a throwaway virtual environment (mutmut 2 counts only the exit code 1 of the test command as a kill, so use a runner that maps every failing exit code to 1):

```
python -m pip install "mutmut<3" pytest cryptography
mutmut run --paths-to-mutate src/hydra_umc_updater/package_release.py --runner "python runner.py tests/test_property_package_release.py tests/test_package_release.py"
mutmut results
```

The run was limited to `package_message`, the checks of the members, `verify_package`, the version helpers, the extraction and `install_package` (the download functions are marked `# pragma: no mutate` in a scratch copy).

| Run | Mutants | Killed | Left |
| --- | --- | --- | --- |
| `package_release.py`, first complete run of the property tests alone | 166 | 128 (77.1 %) | 38, mostly the installation and the texts of the refusals |
| `package_release.py`, after the added tests, up to the installation (99 of the 166 mutants) | 99 | 96 (97.0 %) | 3, equivalent |

The first run showed what the tests did not pin: the limits of a package (the number of members, the unpacked size, the size of the package and of its small files), the texts and codes of the refusals, the rules of the installation (the same version is not newer, a folder that is not an installation is never replaced, the manifest inside the package, a backup is kept and never deleted, a folder deeper than the members that name it) and the signed text written out by hand. The tests now check all of them. The runs after that were cut by their time limit, so the second row covers only the part of the module up to the installation, and the installation itself has not been measured again with the final tests (**pending**). The three mutants left in that part are equivalent: the size of the chunk read when the hash is computed (twice) and a back-slash prefix that the test for a back-slash anywhere in the name catches first.
