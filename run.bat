@echo off
REM =============================================================================
REM HYDRA-UMC-UPDATER - run.bat
REM Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
REM GPL-3.0 - see LICENSE
REM =============================================================================
REM Runs HYDRA-UMC-UPDATER. Run build.bat first.
REM
REM Usage:
REM   run.bat                          - launch the windowed GUI (default)
REM   run.bat --cli status             - what's installed, its version, GitHub's version
REM   run.bat --cli status --offline   - same, without the GitHub check
REM   run.bat --cli install <project>  - clone + build one project not yet installed
REM   run.bat --cli update  <project>  - pull + rebuild one project already installed
cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -m hydra_umc_updater.main %*
pause
