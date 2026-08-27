"""HYDRA-UMC-UPDATER - detects, installs, and manually updates every one of
the HYDRA-UMC/URTC ecosystem's projects on the machine it runs on (the real
CM5, or a dev machine with the same sibling-directory checkout layout).

pyproject.toml's own `version` field is the real source of truth -
`__version__` below is a mirror bump_version.py keeps in sync on every real
build, same convention this ecosystem's other "polished" Python projects
already use (HYDRA-UMC-COGNITIVE-NODE, the Vision-node family, ...) - kept
here (rather than reading it back out of installed package metadata) so
this module has a version to report even before `pip install -e .` has
ever run against a bare checkout.
"""
__version__ = "0.1.6"