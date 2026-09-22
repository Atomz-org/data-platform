"""Creating a group or a project, once, for every caller.

`pf new-group` and `pf new-project` were the only way to bring a tenant into
existence, and the whole sequence lived inside the two Typer commands: resolve
capabilities, plan, write files, apply each capability, merge the gate overlay,
re-render the group card, run the bootstrap ladder. That is fine while the
terminal is the only entrance. It stops being fine the moment a second one
exists, because a second entrance either imports a CLI module — dragging in
Typer, Rich and every command in the file to create a directory — or reimplements
the sequence and starts drifting from it on the first capability anyone adds.

This module is that sequence, with nothing about how it is being asked for. The
CLI keeps its console rendering; the control-plane API keeps its HTTP shape; both
call the same two functions, so a capability registered tomorrow reaches a group
made from a browser and a group made from a shell on the same day.

**Nothing here records provenance.** That is deliberate and it is not an
oversight: an agent running `pf new-project` in a shell is already recorded by
the PreToolUse/PostToolUse hooks, and recording it here as well would write the
same action into the chain twice under two different action ids. The caller that
has no hook covering it — the HTTP route — wraps these in
`pf.provenance.action()` itself. See `pf.ui.provision`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pf.capabilities import (
    Capability,
    UnknownCapability,
    gate_additions,
)
from pf.capabilities import (
    apply as apply_capability,
)
from pf.capabilities import (
    defaults as capability_defaults,
)
from pf.capabilities import (
    resolve as resolve_capabilities,
)
from pf.scaffold import plan as planner
from pf.scaffold.bootstrap import bootstrap
from pf.scaffold.generator import DEFAULT_CLASSES, new_group, new_project

#: Group and project names become directory names, Python module names (via
#: `-` → `_`), dbt profile keys, Dagster code-location names and DuckDB file
#: stems. The intersection of what all of those accept is narrower than what a
#: filesystem accepts, and the failure from picking a name outside it arrives
#: late — at `dbt parse`, or at Dagster load, long after the files exist and
#: `pf new-project` has reported success. Checking here costs one regex.
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

#: Long enough for `<group>-<region>` and a qualifier, short enough that the
#: generated Dagster and dbt identifiers built on top of it stay readable.
NAME_MAX = 40


class ProvisionError(ValueError):
    """A request that must not be scaffolded. Raised rather than corrected: a
    name we silently rewrite is a name the operator will look for and not
    find."""


def validate_name(kind: str, name: str) -> None:
    """Reject a name before anything is written, with the rule in the message.

    `kind` is the word used in the error — "group" or "project" — so the message
    names what the operator was actually typing.
    """
    if not name:
        raise ProvisionError(f"{kind} name is required")
    if len(name) > NAME_MAX:
        raise ProvisionError(f"{kind} name '{name}' is {len(name)} characters; the limit is {NAME_MAX}")
    if not NAME_RE.match(name):
        raise ProvisionError(
            f"invalid {kind} name '{name}' — use lowercase letters, digits and "
            f"single hyphens between them (e.g. 'acme-us'). It becomes a "
            f"directory, a Python module and a dbt profile key."
        )


def domains() -> dict[str, list[str]]:
    """The archetypes `new_group` knows, each with the classes it seeds.

    Read from the generator rather than restated, so the picker in the UI cannot
    offer a fifth archetype the scaffolder would silently fall back to
    `b2b_saas` for.
    """
    return {name: list(classes) for name, classes in DEFAULT_CLASSES.items()}


# ------------------------------------------------------------------ group --
@dataclass
class GroupResult:
    """What creating a group did."""

    group: str
    domain: str
    files: list[Path] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)

    def to_dict(self, root: Path) -> dict[str, Any]:
        return {
            "group": self.group,
            "domain": self.domain,
            "classes": self.classes,
            "files": [str(p.relative_to(root)) for p in self.files],
            "file_count": len(self.files),
        }


def create_group(
    root: Path,
    group: str,
    domain: str = "b2b_saas",
    *,
    display_name: str = "",
    owner_team: str = "",
    owner_contact: str = "",
    tier: str = "standard",
) -> GroupResult:
    """Scaffold a group, then record the identity the scaffold cannot know.

    `new_group` writes a `group.yaml` with an empty `display_name` and no owner,
    because the generator is templated and those are per-tenant facts. Every
    group in this repository still has them empty, which is how `pf offboard`
    came to have nobody to notify. Anything the caller supplies is written in the
    same breath as the directory, while the person who knows the answer is still
    in the room.
    """
    validate_name("group", group)
    if domain not in DEFAULT_CLASSES:
        raise ProvisionError(f"unknown domain '{domain}' — one of: {', '.join(sorted(DEFAULT_CLASSES))}")
    gdir = Path(root) / "groups" / group
    if gdir.exists():
        raise ProvisionError(
            f"group '{group}' already exists at groups/{group} — "
            f"use `pf bootstrap {group}` to bring it up to the current platform"
        )

    files = new_group(Path(root), group, domain)
    _render_group_card(Path(root), group)
    _amend_manifest(
        Path(root),
        group,
        display_name=display_name,
        owner_team=owner_team,
        owner_contact=owner_contact,
        tier=tier,
    )
    return GroupResult(
        group=group,
        domain=domain,
        files=files,
        classes=list(DEFAULT_CLASSES[domain]),
    )


def _amend_manifest(
    root: Path,
    group: str,
    *,
    display_name: str,
    owner_team: str,
    owner_contact: str,
    tier: str,
) -> None:
    """Write the supplied identity fields into a freshly scaffolded group.yaml.

    Goes through `pf.groups.load`/`save` rather than editing the YAML directly,
    so the manifest that lands is the one the loader validates — a tier or a
    lifecycle this platform does not recognise fails now, not at the next gate.
    Absent values are left as the template wrote them; this never blanks a field
    the caller did not mention.
    """
    from pf import groups as groups_mod

    if not any((display_name, owner_team, owner_contact, tier and tier != "standard")):
        return

    m = groups_mod.load(root, group)
    if display_name:
        m.display_name = display_name
    if tier:
        m.tier = tier
    if owner_team or owner_contact:
        m.owner = groups_mod.Owner(
            team=owner_team or m.owner.team,
            contact=owner_contact or m.owner.contact,
        )
    groups_mod.save(m)


# ---------------------------------------------------------------- project --
@dataclass
class ProjectResult:
    """What creating a project did, including the steps that ran after it."""

    group: str
    project: str
    files: list[Path] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    capability_files: dict[str, int] = field(default_factory=dict)
    #: The `section:pattern` entries this scaffold added to the gate overlay.
    #: The entries and not just a count, so a caller can summarise them by
    #: section the way `pf capability-add` does without re-reading the file.
    gate_rules: list[str] = field(default_factory=list)
    #: `pf.scaffold.bootstrap.StepResult`, one per ladder step.
    steps: list[Any] = field(default_factory=list)
    missing_env: dict[str, list[str]] = field(default_factory=dict)

    @property
    def gate_rules_added(self) -> int:
        return len(self.gate_rules)

    @property
    def ok(self) -> bool:
        """Every bootstrap step passed. A project whose ladder half-ran exists
        on disk and is not finished, and the caller has to be able to say so."""
        return all(s.ok for s in self.steps)

    def to_dict(self, root: Path) -> dict[str, Any]:
        return {
            "group": self.group,
            "project": self.project,
            "path": f"groups/{self.group}/projects/{self.project}",
            "files": [str(p.relative_to(root)) for p in self.files],
            "file_count": len(self.files),
            "capabilities": self.capabilities,
            "capability_files": self.capability_files,
            "gate_rules": self.gate_rules,
            "gate_rules_added": self.gate_rules_added,
            "steps": [{"name": s.name, "status": s.status, "detail": s.detail} for s in self.steps],
            "missing_env": self.missing_env,
            "ok": self.ok,
        }


def resolve_capability_set(with_: list[str] | None = None, without: list[str] | None = None) -> list[Capability]:
    """Defaults, plus `with_`, minus `without` — the CLI's rule, shared.

    A project that has to be asked for its capabilities gets the ones whoever
    was asked remembered, which is how seven projects ended up with no CI merge
    gate while the eighth had one. The UI's checkbox list is therefore seeded
    from this, not from an empty set.
    """
    skip = {n.strip() for n in (without or []) if n.strip()}
    names = [n for n in capability_defaults() if n not in skip]
    for n in with_ or []:
        n = n.strip()
        if n and n not in names:
            names.append(n)
    try:
        return resolve_capabilities(names)
    except (UnknownCapability, ValueError) as exc:
        raise ProvisionError(str(exc)) from exc


def plan_project(
    root: Path,
    group: str,
    project: str,
    caps: list[Capability],
    *,
    is_rollup: bool = False,
) -> planner.Plan:
    """Resolve a scaffold against the repository without writing anything.

    A thin pass-through to `pf.scaffold.plan.build` that adds the name check, so
    a bad name surfaces as a blocker in the preview rather than as an exception
    at apply time.
    """
    p = planner.build(Path(root), group, project, caps, is_rollup=is_rollup)
    for kind, name in (("group", group), ("project", project)):
        try:
            validate_name(kind, name)
        except ProvisionError as exc:
            p.blockers.append(str(exc))
    return p


def create_project(
    root: Path,
    group: str,
    project: str,
    *,
    caps: list[Capability] | None = None,
    is_rollup: bool = False,
    sisters: list[str] | None = None,
) -> ProjectResult:
    """Scaffold a project and run everything that has to follow it.

    The order is the order `cmd_new_project` established and is not arbitrary:
    files, then capabilities (which write into those files' directory), then the
    gate overlay (which is derived from the capabilities that were actually
    applied), then the bootstrap ladder (which is shared with `pf bootstrap` and
    is what makes an old project and a new one converge).

    Refuses on any blocker. Scaffolding is cheap to run and expensive to run
    wrong: `pf bootstrap` backfills what is missing but never removes what should
    not have been added.
    """
    root = Path(root)
    caps = list(caps if caps is not None else resolve_capability_set())
    sisters = list(sisters or [])

    resolved = plan_project(root, group, project, caps, is_rollup=is_rollup)
    if not resolved.ok:
        raise ProvisionError("; ".join(resolved.blockers))

    files = new_project(root, group, project, is_rollup=is_rollup, sisters=sisters)

    pdir = root / "groups" / group / "projects" / project
    ctx = {"group": group, "project": project, "module": project.replace("-", "_")}
    written: dict[str, int] = {}
    for cap in caps:
        written[cap.name] = len(apply_capability(cap, root, pdir, ctx))

    added = merge_gate_rules(root, gate_additions(caps)) if caps else []

    # The group card is *not* rendered here: the bootstrap ladder below has a
    # "group card" step that does it, and rendering it twice in one call is how
    # two code paths come to disagree about which one owns the artefact.
    return ProjectResult(
        group=group,
        project=project,
        files=files,
        capabilities=[c.name for c in caps],
        capability_files=written,
        gate_rules=added,
        steps=list(bootstrap(root, group, project)),
        missing_env=dict(resolved.missing_env),
    )


def _render_group_card(root: Path, group: str) -> None:
    """Re-render the group's context card after its membership changes.

    Imported at call time: `pf.kg.card` pulls in the graph stack, and the
    control-plane process should not pay for that at import just to serve
    `/api/tree`. A failure here is not a reason to report a scaffold that
    succeeded as failed — the card is regenerated by `pf bootstrap` as well.
    """
    try:
        from pf.kg.card import render_group_card

        render_group_card(root / "groups" / group, group)
    except Exception:  # noqa: BLE001 — a stale card is a nuisance, not a failure
        pass


def merge_gate_rules(root: Path, additions: dict[str, list[str]]) -> list[str]:
    """Append capability-contributed patterns to the generated gate overlay.

    Written to `gate.capabilities.yaml`, never to `gate.yaml`: round-tripping the
    hand-written policy through the YAML dumper strips every comment in it, and
    those comments are where each rule's reason lives. `load_policy` unions the
    two. Appends only — a capability may tighten the gate, never loosen it.

    Returns the `section:pattern` entries that were new, so a caller can report
    the count without re-reading the file.
    """
    if not additions:
        return []
    path = Path(root) / "gate.capabilities.yaml"
    existing = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing = existing or {}
    changed: list[str] = []
    for section, patterns in additions.items():
        bucket = existing.setdefault(section, [])
        for p in patterns:
            if p not in bucket:
                bucket.append(p)
                changed.append(f"{section}:{p}")
    if changed:
        path.write_text(
            "# GENERATED by `pf new-project --with`. Merged over gate.yaml at load\n"
            "# time by pf.loops.gate.load_policy. Edit the capability, not this file.\n"
            + yaml.safe_dump(existing, sort_keys=False),
            encoding="utf-8",
        )
    return changed
