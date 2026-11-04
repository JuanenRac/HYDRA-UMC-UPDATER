# =============================================================================
# HYDRA-UMC-UPDATER - Persisted user settings: settings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real, local persistence for the small set of choices this GUI should
remember across launches - real user request: the workspace root chosen
via "Browse" used to reset to `default_workspace_root()` (this repo's
own parent directory) on every single launch, with no way to keep a
different one. One JSON file in the user's own home directory, the same
real, simple mechanism `i18n.py`'s own language preference already used
(`~/.hydra_umc_updater_lang.json`) - this module supersedes that file
with a single shared one holding every remembered preference, migrating
a pre-existing language-only file forward the first time it runs so an
already-configured language is never silently lost.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .updater_core import HYDRA_PROFILE as _PROFILE

#: One JSON file in the user's own home directory - holds every real,
#: remembered preference (`lang`, `workspace_root`, ...) as a single flat
#: object, read-modify-write on every save so setting one key never
#: clobbers another.
SETTINGS_PATH = Path.home() / f"{_PROFILE.file_prefix}_settings.json"

#: The old, language-only settings file `i18n.py` used before this
#: module existed - read once, as a migration source, if `SETTINGS_PATH`
#: itself has no `lang` key yet. Never written to again.
_LEGACY_LANG_PATH = Path.home() / f"{_PROFILE.file_prefix}_lang.json"


def load_settings() -> dict[str, Any]:
    """Every real, currently-saved preference. Returns `{}` on a missing
    file, unreadable JSON, or a non-object top level - never raises, same
    "a saved preference is a nice-to-have, not a hard dependency" spirit
    as `i18n.py`'s own original try/except."""
    try:
        raw = SETTINGS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(**updates: Any) -> None:
    """Merges `updates` into whatever is already saved and writes the
    real, combined result back - best-effort, matching `i18n.py`'s own
    non-fatal-on-failure convention (a read-only home directory or a
    permissions issue must never crash the GUI over a saved preference).
    """
    current = load_settings()
    current.update(updates)
    try:
        SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except OSError:
        pass


def get_saved_workspace_root() -> Path | None:
    """The real, previously chosen workspace root, only when it is still
    a real, existing directory on this machine - a saved path pointing
    at a since-deleted/renamed/unmounted location must never be silently
    handed to the rest of this tool as if it were still valid, which
    would make every real project inside it look "not installed"."""
    raw = load_settings().get("workspace_root")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    return path if path.is_dir() else None


def save_workspace_root(path: Path) -> None:
    save_settings(workspace_root=str(path))


def get_saved_lang() -> str | None:
    """Real migration path: prefers the new shared settings file, and
    falls back to the legacy language-only file (never written again
    once this module exists) so an already-configured language survives
    the switch to this shared file instead of silently resetting to the
    OS locale/English on the next launch."""
    lang = load_settings().get("lang")
    if isinstance(lang, str) and lang:
        return lang
    try:
        raw = _LEGACY_LANG_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        legacy_lang = data.get("lang") if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    return legacy_lang if isinstance(legacy_lang, str) and legacy_lang else None


def save_lang(lang: str) -> None:
    save_settings(lang=lang)


def settings_file_is_damaged() -> bool:
    """True when the settings file exists but cannot be read as a JSON object.
    Used to fail closed: a damaged file must never silently switch off a
    safety setting that may have been stored in it."""
    if not SETTINGS_PATH.exists():
        return False
    try:
        return not isinstance(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")), dict)
    except (OSError, ValueError):
        return True


def get_require_signed_commits() -> bool:
    """Whether the saved settings ask for signed commits. A damaged settings
    file counts as "yes" (fail closed)."""
    if settings_file_is_damaged():
        return True
    return load_settings().get("require_signed_commits") is True


def save_require_signed_commits(required: bool) -> None:
    save_settings(require_signed_commits=bool(required))


def get_recreate_venv() -> bool:
    """Whether a promoted checkout gets a fresh `.venv` when the previous installation had one.
    On unless the saved settings say otherwise; a damaged file keeps the default."""
    if settings_file_is_damaged():
        return True
    return load_settings().get("recreate_venv") is not False


def save_recreate_venv(enabled: bool) -> None:
    save_settings(recreate_venv=bool(enabled))


def get_os_deploy() -> bool:
    """Whether a promoted project is deployed on the device with `hydra-umc-os deploy` (its installer, a restart of the unit if it runs, a health
    check and the way back). Off unless the saved settings say so; a damaged file keeps it off."""
    if settings_file_is_damaged():
        return False
    return load_settings().get("os_deploy") is True


def save_os_deploy(enabled: bool) -> None:
    save_settings(os_deploy=bool(enabled))


def get_allowed_signers_file() -> str | None:
    """Path of the ssh allowed-signers file used to verify commit signatures,
    only when it is a real file."""
    raw = load_settings().get("allowed_signers_file")
    if isinstance(raw, str) and raw and Path(raw).is_file():
        return raw
    return None


def save_allowed_signers_file(path: Path | str) -> None:
    save_settings(allowed_signers_file=str(path))


def get_evidence_export() -> bool:
    """Whether the evidence of the attempts may be exported to an outbox file and, when an address is set, pushed to the data lake. Off unless the saved
    settings say so; a damaged file keeps it off."""
    if settings_file_is_damaged():
        return False
    return load_settings().get("evidence_export") is True


def save_evidence_export(enabled: bool) -> None:
    save_settings(evidence_export=bool(enabled))


def _text_setting(key: str) -> str | None:
    raw = load_settings().get(key)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def get_evidence_export_url() -> str | None:
    """Base address of the data lake (`http://host:port`) that receives the evidence, or None to keep it in the outbox file only."""
    return _text_setting("evidence_export_url")


def get_evidence_export_token_file() -> str | None:
    """File that holds the ingest token of the data lake (the token itself is never kept in the settings)."""
    return _text_setting("evidence_export_token_file")


def get_evidence_export_allow_plain_http() -> bool:
    """Whether the evidence may travel over plain HTTP to an address that is not this machine. Off by default; a damaged file keeps it off."""
    if settings_file_is_damaged():
        return False
    return load_settings().get("evidence_export_allow_plain_http") is True


def get_node_name() -> str | None:
    """The name this machine gives itself in the exported evidence (default: its host name)."""
    return _text_setting("node_name")


def get_device_root() -> str | None:
    """Folder that holds the installed programs of the device when it is not `/opt/hydra-umc` (a mounted image, a test tree)."""
    return _text_setting("device_root")


def get_image_release_trusted_keys() -> str | None:
    """File with the trusted PUBLIC keys that may sign a release of an operating-system image (never a private key)."""
    return _text_setting("image_release_trusted_keys")


def get_image_release_require_tag() -> bool:
    """Whether a release of an image must also have a signed git tag on the same commit. Off by default; a damaged file keeps it off
    (the signature of the manifest is always required, whatever this says)."""
    if settings_file_is_damaged():
        return False
    return load_settings().get("image_release_require_tag") is True


def get_image_release_repo() -> str | None:
    """Local clone in which the signed tag of a release is checked."""
    return _text_setting("image_release_repo")


#: Channels from which the updater takes releases. "stable" is the only one used unless the saved settings name the other.
RELEASE_CHANNELS = ("stable", "pruebas")


def get_release_channel() -> str:
    """The channel the updater installs from: "stable" (the latest published release that is not a draft or a pre-release) unless the saved settings
    say "pruebas" (the latest release including pre-releases). Anything else, and a damaged file, keeps "stable"."""
    if settings_file_is_damaged():
        return "stable"
    value = load_settings().get("release_channel")
    return value if value == "pruebas" else "stable"


def save_release_channel(channel: str) -> None:
    save_settings(release_channel=channel if channel in RELEASE_CHANNELS else "stable")


def get_require_signed_packages() -> bool:
    """Whether a package of a release must carry a valid Ed25519 signature by the key of the releases before it is installed. On unless the saved
    settings say `false`; a damaged file keeps it on (fail closed)."""
    if settings_file_is_damaged():
        return True
    return load_settings().get("require_signed_packages") is not False


def save_require_signed_packages(required: bool) -> None:
    save_settings(require_signed_packages=bool(required))
