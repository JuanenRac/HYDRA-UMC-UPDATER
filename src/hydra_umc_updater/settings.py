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

#: One JSON file in the user's own home directory - holds every real,
#: remembered preference (`lang`, `workspace_root`, ...) as a single flat
#: object, read-modify-write on every save so setting one key never
#: clobbers another.
SETTINGS_PATH = Path.home() / ".hydra_umc_updater_settings.json"

#: The old, language-only settings file `i18n.py` used before this
#: module existed - read once, as a migration source, if `SETTINGS_PATH`
#: itself has no `lang` key yet. Never written to again.
_LEGACY_LANG_PATH = Path.home() / ".hydra_umc_updater_lang.json"


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
