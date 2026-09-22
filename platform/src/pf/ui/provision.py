"""The control plane's one writing surface for tenancy: fleet, and provisioning.

Everything else the dashboard serves answers "what is here". This answers "make
something that is not here yet", which is a different kind of route and is kept
in its own module for that reason rather than for file length.

Three rules it follows, none of them negotiable:

- **It never reimplements the scaffolder.** Every write goes through
  `pf.scaffold.provision`, the same two functions `pf new-group` and
  `pf new-project` call. A capability registered tomorrow reaches a project made
  from this UI without anyone editing this file. The alternative — a second
  implementation of "create a project" behind HTTP — is how the browser and the
  terminal come to produce different projects from the same inputs.
- **`actor` is required and never defaulted.** Same rule as the governance
  writes: a record whose author column can be blank says something was created
  and nothing about who decided to create a tenant.
- **Every write is wrapped in `pf.provenance.action()`.** A click in a browser
  has no PreToolUse hook over it, so the three provenance stages that a shell
  command gets for free have to be written here or not at all. Creating a tenant
  is precisely the action that must not be missing from the chain.

Bodies are JSON, not query parameters, unlike the governance routes. A project
is created with a list of capabilities and a list of sisters, and lists in a
query string are the kind of encoding detail that eventually disagrees between
the two ends. The governance routes edit one scalar at a time and are right to
stay as they are.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pf import obs, provenance
from pf.scaffold import provision as scaffold

router = APIRouter(prefix="/api", tags=["provision"])


def root_dir() -> Path:
    return obs.repo_root()


# ------------------------------------------------------------------ fleet --
def _warehouse_of(pdir: Path) -> str:
    """The dbt `prod` output's type, which is what this project ships onto.

    Read from the generated `profiles.yml` rather than from the capability list
    because the profile is what dbt actually obeys. A project whose warehouse
    capability was swapped by hand would otherwise be reported as its original
    one forever.
    """
    prof = pdir / "transform" / "profiles.yml"
    if not prof.is_file():
        return ""
    try:
        raw = yaml.safe_load(prof.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return ""
    for name, block in raw.items():
        if name == "elementary" or not isinstance(block, dict):
            continue
        outputs = block.get("outputs") or {}
        target = outputs.get("prod") or outputs.get("dev") or {}
        if isinstance(target, dict) and target.get("type"):
            return str(target["type"])
    return ""


#: The node kinds the fleet list puts in its own columns, in the spelling
#: `pf.kg.store.NODE_KINDS` uses. Capitalised, and that is the whole point: the
#: lowercase guess reported nought models for a project with thirty-seven, which
#: is the same fault as a green nought over an unmeasured project — a clean bill
#: of health nobody issued. Asserted against the real tuple in the tests.
HEADLINE_KINDS = {"models": "Model", "sources": "Source", "metrics": "Metric", "tests": "Test"}


def headline_counts(counts: dict[str, int]) -> dict[str, int | None]:
    """The four figures the fleet table shows, or `None` for an ungraphed project.

    `None` rather than `0` is load-bearing. "Graphed, and it holds no metrics" and
    "never graphed" are different facts about a project, and a table that renders
    both as a zero tells an operator the second one is fine.
    """
    if not counts:
        return dict.fromkeys(HEADLINE_KINDS, None)
    return {label: counts.get(kind, 0) for label, kind in HEADLINE_KINDS.items()}


def _project_row(root: Path, group: str, pdir: Path) -> dict[str, Any]:
    from pf.kg.store import open_graph

    gp = pdir / "kg" / "graph.duckdb"
    counts: dict[str, int] = {}
    if gp.is_file():
        try:
            with open_graph(gp, read_only=True) as gr:
                counts = gr.counts()
        except Exception:  # noqa: BLE001 — a locked or half-built graph is a
            counts = {}  # display gap, not a reason to fail the fleet list

    return {
        "group": group,
        "name": pdir.name,
        "path": f"groups/{group}/projects/{pdir.name}",
        "is_rollup": pdir.name.endswith("-rollup"),
        "has_graph": gp.is_file(),
        "counts": counts,
        **headline_counts(counts),
        "warehouse": _warehouse_of(pdir),
        "has_dbt": (pdir / "transform" / "dbt_project.yml").is_file(),
        "has_pipelines": (pdir / "src").is_dir(),
    }


@router.get("/fleet")
def fleet() -> dict[str, Any]:
    """Every group and every project, with the manifest facts the tree omits.

    `/api/tree` answers "what may I select" and is deliberately cheap. This
    answers "what do we operate" — lifecycle, owner, tier, template drift — which
    is the list a platform operator actually works from, and the one a create
    button belongs beside.
    """
    from pf import groups as groups_mod

    root = root_dir()
    gdir = root / "groups"
    out: list[dict[str, Any]] = []
    unmanaged: list[str] = []

    if gdir.is_dir():
        for g in sorted(p for p in gdir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            manifest: dict[str, Any] = {}
            error = ""
            if groups_mod.exists(root, g.name):
                try:
                    m = groups_mod.load(root, g.name)
                    manifest = {
                        "display_name": m.display_name,
                        "domain": m.domain,
                        "lifecycle": m.lifecycle,
                        "tier": m.tier,
                        "owner_team": m.owner.team,
                        "owner_contact": m.owner.contact,
                        "template_version": m.template_version,
                        "behind_template": m.behind_template,
                        "runs_loops": m.runs_loops,
                        "strict": m.strict,
                        "residency": m.data.residency,
                    }
                except groups_mod.GroupError as exc:
                    # Surfaced, not swallowed. A malformed manifest is the one
                    # case where the operator must see the group *and* the fault.
                    error = str(exc)
            else:
                unmanaged.append(g.name)

            pdir = g / "projects"
            projects = (
                [
                    _project_row(root, g.name, p)
                    for p in sorted(x for x in pdir.iterdir() if x.is_dir() and not x.name.startswith("."))
                ]
                if pdir.is_dir()
                else []
            )

            inst = g / "ontology" / "instance.yaml"
            classes: list[str] = []
            if inst.is_file():
                raw = yaml.safe_load(inst.read_text(encoding="utf-8")) or {}
                classes = list(raw.get("classes") or [])

            out.append(
                {
                    "name": g.name,
                    "classes": classes,
                    "projects": projects,
                    "project_count": len(projects),
                    "error": error,
                    "template_version_current": groups_mod.TEMPLATE_VERSION,
                    **manifest,
                }
            )

    return {
        "root": str(root),
        "groups": out,
        "unmanaged": unmanaged,
        "counts": {
            "groups": len(out),
            "projects": sum(g["project_count"] for g in out),
            "active": sum(1 for g in out if g.get("lifecycle") == "active"),
            "behind_template": sum(1 for g in out if g.get("behind_template")),
        },
    }


# ---------------------------------------------------------------- options --
@router.get("/provision/options")
def options() -> dict[str, Any]:
    """Everything the create forms need, in one call.

    The UI names no domain, no capability and no warehouse of its own. All three
    registries are asked at request time, for the same reason `/api/tools` asks
    the tool registry: registering the thing stays the only step, and a picker
    cannot offer an option the scaffolder would silently ignore.
    """
    from pf.capabilities import CAPABILITIES
    from pf.capabilities import defaults as capability_defaults
    from pf.groups import LIFECYCLE, TIERS
    from pf.runtime.targets import WAREHOUSES

    defaults = set(capability_defaults())
    warehouse_names = set(WAREHOUSES)

    caps = [
        {
            "name": c.name,
            "description": c.description,
            "default": c.name in defaults,
            "is_warehouse": c.name in warehouse_names,
            "files": len(c.files),
            "env": list(c.env),
            "requires": list(c.requires),
        }
        for c in sorted(CAPABILITIES.values(), key=lambda c: c.name)
    ]

    return {
        "domains": [{"name": n, "classes": cs} for n, cs in sorted(scaffold.domains().items())],
        "capabilities": caps,
        "defaults": sorted(defaults),
        "warehouses": sorted(warehouse_names),
        "lifecycles": list(LIFECYCLE),
        "tiers": list(TIERS),
        "groups": sorted(
            p.name for p in (root_dir() / "groups").iterdir() if p.is_dir() and not p.name.startswith(".")
        ),
        "name_rule": scaffold.NAME_RE.pattern,
        "name_max": scaffold.NAME_MAX,
    }


# ------------------------------------------------------------------ write --
class NewGroup(BaseModel):
    group: str
    domain: str = "b2b_saas"
    display_name: str = ""
    owner_team: str = ""
    owner_contact: str = ""
    tier: str = "standard"
    actor: str = Field(default="", description="who is creating this tenant")
    reason: str = ""


class NewProject(BaseModel):
    group: str
    project: str
    rollup: bool = False
    sisters: list[str] = Field(default_factory=list)
    #: Capability names on top of the registry defaults.
    with_: list[str] = Field(default_factory=list, alias="with")
    #: Default capability names to skip.
    without: list[str] = Field(default_factory=list)
    actor: str = Field(default="", description="who is creating this project")
    reason: str = ""

    model_config = {"populate_by_name": True}


def _require_actor(actor: str) -> str:
    if not actor.strip():
        raise HTTPException(
            400,
            "actor is required — a tenant created by nobody is a record of a change with no decision attached to it",
        )
    return actor.strip()


@router.post("/provision/group/plan")
def plan_group(body: NewGroup) -> dict[str, Any]:
    """What creating this group would do, and what would stop it. Writes nothing.

    Deliberately mirrors `pf new-project --plan`: the blockers are the point. A
    preview that lists what *would* happen but not what would *stop* it is one
    you still have to try before you trust.
    """
    blockers: list[str] = []
    try:
        scaffold.validate_name("group", body.group)
    except scaffold.ProvisionError as exc:
        blockers.append(str(exc))

    if (root_dir() / "groups" / body.group).exists():
        blockers.append(f"groups/{body.group} already exists")

    domains = scaffold.domains()
    if body.domain not in domains:
        blockers.append(f"unknown domain '{body.domain}' — one of: {', '.join(sorted(domains))}")

    warnings: list[str] = []
    if not body.owner_team and not body.owner_contact:
        # Not a blocker: a group with no owner still scaffolds, and refusing
        # here would make the form harder than the CLI for no safety gain. It is
        # a warning because `pf offboard` has nobody to notify without it, and
        # the cheapest moment to record an owner is now.
        warnings.append("no owner recorded — pf offboard and the loop budget have nobody to attribute this family to")

    return {
        "group": body.group,
        "domain": body.domain,
        "classes": domains.get(body.domain, []),
        "path": f"groups/{body.group}",
        "blockers": blockers,
        "warnings": warnings,
        "ok": not blockers,
    }


@router.post("/provision/group")
def create_group(body: NewGroup) -> dict[str, Any]:
    """Create a group. The write, recorded."""
    actor = _require_actor(body.actor)
    root = root_dir()

    try:
        with provenance.action(
            root,
            tool="pf.ui.provision",
            target=f"groups/{body.group}",
            summary=f"{actor} created group '{body.group}' ({body.domain})"
            + (f" — {body.reason}" if body.reason else ""),
            group=body.group,
        ) as rec:
            result = scaffold.create_group(
                root,
                body.group,
                body.domain,
                display_name=body.display_name,
                owner_team=body.owner_team,
                owner_contact=body.owner_contact,
                tier=body.tier,
            )
            rec["detail"] = f"{len(result.files)} file(s)"
    except scaffold.ProvisionError as exc:
        raise HTTPException(400, str(exc)) from exc

    payload = result.to_dict(root)
    payload["actor"] = actor
    payload["next"] = f"pf new-project {body.group} {body.group}-us"
    return payload


@router.post("/provision/project/plan")
def plan_project(body: NewProject) -> dict[str, Any]:
    """Resolve the scaffold against the repository. Writes nothing.

    The same `pf.scaffold.plan` the CLI renders as text, as JSON. Both ends
    therefore agree about what blocks a scaffold, because there is one function
    that decides.
    """
    root = root_dir()
    try:
        caps = scaffold.resolve_capability_set(body.with_, body.without)
    except scaffold.ProvisionError as exc:
        return {
            "group": body.group,
            "project": body.project,
            "blockers": [str(exc)],
            "warnings": [],
            "capabilities": [],
            "missing_env": {},
            "gate_rules_added": 0,
            "ok": False,
        }

    from pf.capabilities import gate_additions

    p = scaffold.plan_project(root, body.group, body.project, caps, is_rollup=body.rollup)
    rules = gate_additions(caps)

    return {
        "group": body.group,
        "project": body.project,
        "path": f"groups/{body.group}/projects/{body.project}",
        "is_rollup": body.rollup,
        "capabilities": [{"name": c.name, "files": len(c.files), "ci": sorted(c.ci_jobs)} for c in caps],
        "gate_rules_added": sum(len(v) for v in rules.values()),
        "missing_env": p.missing_env,
        "blockers": p.blockers,
        "warnings": p.warnings,
        "ok": p.ok,
    }


@router.post("/provision/project")
def create_project(body: NewProject) -> dict[str, Any]:
    """Create a project: scaffold, capabilities, gate overlay, bootstrap ladder.

    Returns every bootstrap step with its status rather than a single boolean.
    A project whose ladder half-ran exists on disk and is not finished, and
    "created ✓" over a failed graph build is the report that costs someone an
    afternoon.
    """
    actor = _require_actor(body.actor)
    root = root_dir()

    try:
        caps = scaffold.resolve_capability_set(body.with_, body.without)
        with provenance.action(
            root,
            tool="pf.ui.provision",
            target=f"groups/{body.group}/projects/{body.project}",
            summary=f"{actor} created project '{body.group}/{body.project}'"
            + (" (roll-up)" if body.rollup else "")
            + (f" — {body.reason}" if body.reason else ""),
            group=body.group,
            project=body.project,
        ) as rec:
            result = scaffold.create_project(
                root,
                body.group,
                body.project,
                caps=caps,
                is_rollup=body.rollup,
                sisters=body.sisters,
            )
            failed = [s.name for s in result.steps if not s.ok]
            rec["detail"] = f"{len(result.files)} file(s), {len(caps)} capability(ies)" + (
                f"; bootstrap failed: {', '.join(failed)}" if failed else ""
            )
    except scaffold.ProvisionError as exc:
        raise HTTPException(400, str(exc)) from exc

    payload = result.to_dict(root)
    payload["actor"] = actor
    return payload
