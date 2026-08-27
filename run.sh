#!/usr/bin/env bash
# =============================================================================
# HYDRA-UMC-UPDATER - run.sh
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
# Runs HYDRA-UMC-UPDATER. Run ./build.sh first.
#
# Usage:
#   ./run.sh                             - launch the windowed GUI (default)
#   ./run.sh --cli status                - what's installed, its version, GitHub's version
#   ./run.sh --cli status --offline      - same, without the GitHub check
#   ./run.sh --cli install <project>     - clone + build one project not yet installed
#   ./run.sh --cli update  <project>     - pull + rebuild one project already installed
# --cli never needs tkinter/a display - safe on a headless CM5 with no
# python3-tk installed. See main.py's own header comment.
set -uo pipefail  # no -e: we need to reach the trap below even if the process exits non-zero
cd "$(dirname "$0")"

# Keep the window open if this was double-clicked instead of run from an
# already-open terminal - matters most for `--cli status` (real output a
# double-click would otherwise flash-close before it's readable); the
# default GUI mode already blocks on its own mainloop, so this only adds
# one harmless extra prompt there. Only prompts when stdin is actually a
# terminal (never in CI/piped/non-interactive runs).
trap '[ -t 0 ] && read -r -p "Press Enter to close..." _' EXIT

if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
    # shellcheck disable=SC1091
    source .venv/Scripts/activate
fi

python -m hydra_umc_updater.main "$@"
exit $?
