# =============================================================================
# HYDRA-UMC-UPDATER - Deployment plan: deploy_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""What would have to be deployed on the device so that it runs what the workspace has.

The plan crosses three things that already exist: the table of installers of
HYDRA-UMC-OS (which program is installed where, as which unit, under which
deployment contract), the manifest of every checkout in the workspace (the version
that was promoted and the dependencies) and the manifest each installer leaves next
to the installed program (the version that runs). The result is a list of steps in
dependency order with the version on the device, the version in the checkout and the
command that would deploy it. Building the plan only reads files: it installs
nothing, runs nothing and needs no privileges.

`apply_plan` is the only part that acts, and it reuses the deployment of the updater
(`hydra-umc-os deploy`, with its health check and its way back): it does nothing
unless the `os_deploy` switch is on and the call says `confirmed`, it checks the
signature of the checkout first whenever signatures are required, it stops at the
first step that does not hold, and it leaves one line of evidence per step."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import install, settings
from .evidence import installed_state, record_attempt
from .project_manifest import ManifestValidationError, parse_manifest
from .updater_core import HYDRA_PROFILE, EcosystemProfile
from .version_parse import Version

#: where the installers put the programs when nothing else is said
DEFAULT_DEVICE_ROOT = "/opt/hydra-umc"
PLAN_FORMAT_PREFIX = "hydra-install-plan/"

# the state of one program, as the plan reports it
DEPLOY = "deploy"
CURRENT = "current"
AHEAD = "ahead"
NOT_INSTALLED = "not-installed"
NO_CHECKOUT = "no-checkout"
MANUAL = "manual"
NOT_CM5 = "not-cm5"
UNKNOWN = "unknown"


class PlanError(RuntimeError):
    """The table of installers cannot be used."""


@dataclass(frozen=True)
class PlanRow:
    project: str
    state: str
    checkout_version: str | None
    device_version: str | None
    unit: str | None
    target: str | None
    command: tuple[str, ...] | None
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "state": self.state,
            "checkoutVersion": self.checkout_version,
            "deviceVersion": self.device_version,
            "unit": self.unit,
            "target": self.target,
            "command": list(self.command) if self.command else None,
            "note": self.note,
        }


@dataclass
class DeployPlan:
    rows: list[PlanRow] = field(default_factory=list)

    @property
    def steps(self) -> list[PlanRow]:
        return [row for row in self.rows if row.state == DEPLOY]

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "steps": len(self.steps), "projects": [row.as_dict() for row in self.rows]}


def device_root() -> str:
    return HYDRA_PROFILE.env_text("DEVICE_ROOT") or settings.get_device_root() or DEFAULT_DEVICE_ROOT


def default_install_plan(workspace_root: Path) -> Path:
    return workspace_root / "HYDRA-UMC-OS" / "provisioning" / "install_plan.json"


def load_install_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanError(f"the table of installers {path} cannot be read: {exc}") from exc
    if (
        not isinstance(data, dict)
        or not str(data.get("format", "")).startswith(PLAN_FORMAT_PREFIX)
        or not isinstance(data.get("installers"), list)
        or not isinstance(data.get("supported_contract"), int)
    ):
        raise PlanError(f"{path} is not a table of installers this updater understands")
    return data


def _remap(target: str, root: str) -> str:
    """The installed path on this machine: the installers write below `/opt/hydra-umc`, and `root` says where that tree is here."""
    if root.rstrip("/") == DEFAULT_DEVICE_ROOT:
        return target
    if target == DEFAULT_DEVICE_ROOT or target.startswith(DEFAULT_DEVICE_ROOT + "/"):
        return root.rstrip("/\\") + target[len(DEFAULT_DEVICE_ROOT):]
    return target


def _read_manifest(path: Path, name: str, profile: EcosystemProfile):
    try:
        return parse_manifest(path.read_text(encoding="utf-8"), expected_name=name, ecosystem_id=profile.ecosystem_id)
    except (OSError, ManifestValidationError):
        return None


def _version(text: str | None) -> Version | None:
    try:
        return Version.from_string(text) if text else None
    except ValueError:
        return None


def build_plan(
    workspace_root: Path,
    *,
    install_plan: Path | None = None,
    root: str | None = None,
    profile: EcosystemProfile = HYDRA_PROFILE,
    command_for: Callable[[str], list[str] | None] = install.os_deploy_command,
) -> DeployPlan:
    """The plan for the workspace. Reads only."""
    table = load_install_plan(install_plan or default_install_plan(workspace_root))
    device = root or device_root()
    rows: list[PlanRow] = []
    depends: dict[str, tuple[str, ...]] = {}
    for installer in table["installers"]:
        project = installer.get("source")
        if not isinstance(project, str) or not project:
            continue  # the base installer and the like: nothing of the workspace to compare
        unit = installer.get("unit") if isinstance(installer.get("unit"), str) else None
        target = _remap(installer["target"], device) if isinstance(installer.get("target"), str) else None
        manifest = _read_manifest(workspace_root / project / profile.manifest_file, project, profile)
        if manifest is None:
            rows.append(PlanRow(project, NO_CHECKOUT, None, None, unit, target, None, "the project is not checked out in the workspace or its manifest is not valid"))
            continue
        depends[project] = manifest.depends_on
        if manifest.deployment_target != "cm5":
            rows.append(PlanRow(project, NOT_CM5, manifest.version, None, unit, target, None, f"its deployment target is {manifest.deployment_target}"))
            continue
        if installer.get("contract") != table["supported_contract"]:
            reason = installer.get("deploy_exempt") or "its installer does not follow the deployment contract this updater supports"
            rows.append(PlanRow(project, MANUAL, manifest.version, None, unit, target, None, str(reason)))
            continue
        installed_text: str | None = None
        if target:
            installed = _read_manifest(Path(target) / profile.manifest_file, project, profile)
            installed_text = installed.version if installed else None
        if installed_text is None:
            exists = bool(target) and Path(str(target)).is_dir()
            if exists:
                rows.append(PlanRow(project, UNKNOWN, manifest.version, None, unit, target, None, "installed, but the version on the device cannot be read"))
            else:
                rows.append(PlanRow(project, NOT_INSTALLED, manifest.version, None, unit, target, None, "not installed on the device; a first installation is done by hand with its installer, never by this plan"))
            continue
        checkout, running = _version(manifest.version), _version(installed_text)
        if checkout is None or running is None:
            rows.append(PlanRow(project, UNKNOWN, manifest.version, installed_text, unit, target, None, "a version cannot be compared"))
        elif running < checkout:
            rows.append(PlanRow(project, DEPLOY, manifest.version, installed_text, unit, target, tuple(command_for(project) or ()) or None, "the device runs an older version"))
        elif checkout < running:
            rows.append(PlanRow(project, AHEAD, manifest.version, installed_text, unit, target, None, "the device runs a newer version than the checkout; nothing to do"))
        else:
            rows.append(PlanRow(project, CURRENT, manifest.version, installed_text, unit, target, None, "the device runs the version of the checkout"))
    order = install.order_batch([row.project for row in rows], depends)
    rank = {name: index for index, name in enumerate(order)}
    rows.sort(key=lambda row: rank[row.project])
    return DeployPlan(rows)


def format_plan(plan: DeployPlan) -> str:
    width = max((len(row.project) for row in plan.rows), default=7) + 2
    lines = [f"{'PROJECT':<{width}}{'STATE':<15}{'CHECKOUT':<11}{'DEVICE':<11}NOTE"]
    for row in plan.rows:
        lines.append(f"{row.project:<{width}}{row.state:<15}{row.checkout_version or '-':<11}{row.device_version or '-':<11}{row.note}")
    lines.append("")
    lines.append(f"{len(plan.steps)} step(s) to deploy; this is a plan, nothing was changed.")
    return "\n".join(lines)


@dataclass(frozen=True)
class ApplyOutcome:
    ok: bool
    messages: tuple[str, ...]


def apply_plan(
    plan: DeployPlan,
    workspace_root: Path,
    *,
    confirmed: bool,
    deploy: Callable[[str], install.OsDeployOutcome] = install.run_os_deploy,
    verify_signature: Callable[[Path], tuple[bool, str]] = install.verify_candidate_signature,
    profile: EcosystemProfile = HYDRA_PROFILE,
) -> ApplyOutcome:
    """Deploy the steps in order. Needs `confirmed` and the `os_deploy` switch; stops at the first step that fails."""
    if not confirmed:
        return ApplyOutcome(False, ("nothing was deployed: the plan is applied only with an explicit confirmation",))
    if not install.os_deploy_enabled():
        return ApplyOutcome(False, ("nothing was deployed: the deployment on the device is switched off (os_deploy or HYDRA_UMC_UPDATER_OS_DEPLOY=1)",))
    messages: list[str] = []
    for row in plan.steps:
        checkout = workspace_root / row.project
        if install.signature_required():
            signed, detail = verify_signature(checkout)
            if not signed:
                text = f"{row.project}: the signature of the checkout is not valid ({detail}); nothing else was deployed"
                record_attempt(workspace_root, project=row.project, before={"version": row.device_version}, after={"version": row.device_version}, ok=False, message=text)
                return ApplyOutcome(False, (*messages, text))
        outcome = deploy(row.project)
        done = outcome.status == "deployed"
        text = f"{row.project}: {outcome.status} - {outcome.message}"
        record_attempt(
            workspace_root,
            project=row.project,
            before={"version": row.device_version},
            after={"version": installed_state(checkout).get("version") if done else row.device_version, "commit": installed_state(checkout).get("commit")},
            ok=done,
            message=f"deploy plan: {text}",
        )
        messages.append(text)
        if not done:
            return ApplyOutcome(False, (*messages, "stopped here; the steps after this one were not deployed"))
    return ApplyOutcome(True, (*messages, f"{len(plan.steps)} step(s) deployed"))
