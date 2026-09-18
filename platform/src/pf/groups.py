"""The group as an object: who owns it, what state it is in, what it owns.

A group used to be a directory. Everything the platform knew about one was
inferred from the filesystem — `all_projects()` walks `groups/*/projects/*`, the
archetype hid in `ontology/instance.yaml`, and nothing recorded an owner, a
contract, or whether the family was still a customer. That is workable while a
person remembers every tenant. It stops being workable at the first offboarding,
because nothing can answer "what does this group own" and nothing notices that
the answer has stopped mattering.

`group.yaml` is that missing object. It is hand-owned, small, and read by three
things that could not exist without it:

- **`pf group verify`** — a definition of done. The per-project ladder
  (`pf align`) already answers "is this entity modelled"; nothing answered "is
  this family onboarded", so a group with no projects passed every gate in the
  repo by having nothing to fail.
- **`pf offboard`** — the inverse of bootstrap. A removal has to enumerate what
  lives outside `groups/<g>/`, including resources in systems the repo can only
  write to, and a manifest is the only place those handles can be written down
  while someone still knows them.
- **the gates** — strictness proportional to lifecycle. Missing annotations are
  a warning in a group still being built and an error in one declared `active`.
  Without a state, a gate has to choose one severity for both, and choosing the
  strict one is how five of nine projects came to be permanently yellow.

## Lifecycle

    proposed -> provisioned -> active -> suspended -> active
                                    \\-> offboarding -> archived

`proposed` is a directory and an intention. `provisioned` means the scaffold ran
and the plumbing exists. `active` is the only state the strict gates apply to,
and the only one whose loops run. `suspended` is a live tenant deliberately
paused: loops stop, the data stays, the gates keep judging it. `offboarding` is a
decision to leave with the data still present, which is what makes an export
possible. `archived` is the tombstone left behind after the directory goes, so a
name cannot be silently reused and a later question about a departed tenant has
somewhere to land.

Transitions are checked because the interesting ones are irreversible: nothing
goes from `archived` back to `active`, and nothing reaches `archived` without
passing through `offboarding`, where the export happens.

## Template version

`template_version` records the scaffold generation a group was created with.
`pf bootstrap` raises it as it backfills. Its only job is to make drift
*visible*: the platform gained `loops.yaml` and a plugin manifest after four of
the five groups existed, and the only signal was a fleet-wide readiness check
that said "4 unresolvable" and cost five points. A version a human can compare is
cheaper than a symptom.

## Schema: groups/<group>/group.yaml

    schema_version: 1
    group: commodity              # must match the directory
    display_name: Commodity Desks
    domain: commodities           # archetype; the ontology instance agrees
    lifecycle: active
    template_version: 3
    owner:
      team: data-platform
      contact: someone@example.com
    tier: standard                # standard | critical
    data:
      residency: local            # where this family's data is allowed to live
      retention_days: 3650        # null = keep indefinitely
      erasure_sla_days: 30        # null = no contractual deadline
    budget:
      daily_tokens: 40000         # this family's share of agent spend
    resources:                    # handles the repo can write to but not enumerate
      artifact_prefix: groups/commodity
      catalog_services: [commodity_*]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Raised when the scaffold's group templates change in a way an existing group
# has to catch up with. `pf bootstrap` writes the current value; `pf group
# verify` reports a group that is behind.
TEMPLATE_VERSION = 3

LIFECYCLE: tuple[str, ...] = (
    "proposed", "provisioned", "active", "suspended", "offboarding", "archived",
)

# Where a state may go next. Absent from a value's tuple means refused, and the
# refusals are the point: archived is terminal, and archived is only reachable
# through offboarding, which is where the export happens.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "proposed": ("provisioned", "archived"),
    "provisioned": ("active", "offboarding"),
    "active": ("suspended", "offboarding"),
    "suspended": ("active", "offboarding"),
    "offboarding": ("archived", "active"),
    "archived": (),
}

# The states whose loops run and whose gates are strict.
RUNNING = ("active",)
STRICT = ("active", "suspended")

TIERS = ("standard", "critical")
MANIFEST = "group.yaml"


class GroupError(Exception):
    """A manifest that cannot be trusted. Raised rather than defaulted: a group
    whose identity file is malformed is exactly the case where guessing is
    worse than stopping."""


@dataclass(frozen=True)
class Owner:
    team: str = ""
    contact: str = ""


@dataclass(frozen=True)
class DataPolicy:
    """What was promised about this family's data. `retention_days` and
    `erasure_sla_days` are `None` when nothing was promised, which is different
    from zero and has to stay different: `pf offboard` reports "no deadline
    recorded" rather than inventing one."""
    residency: str = ""
    retention_days: int | None = None
    erasure_sla_days: int | None = None


@dataclass
class Manifest:
    group: str
    path: Path
    schema_version: int = 1
    display_name: str = ""
    domain: str = ""
    lifecycle: str = "proposed"
    template_version: int = 0
    tier: str = "standard"
    owner: Owner = field(default_factory=Owner)
    data: DataPolicy = field(default_factory=DataPolicy)
    daily_tokens: int | None = None
    resources: dict[str, Any] = field(default_factory=dict)

    @property
    def runs_loops(self) -> bool:
        return self.lifecycle in RUNNING

    @property
    def strict(self) -> bool:
        """Whether a gate should treat a shortfall as an error. A family still
        being built is allowed to be incomplete; one declared live is not."""
        return self.lifecycle in STRICT

    @property
    def behind_template(self) -> bool:
        return self.template_version < TEMPLATE_VERSION

    def to_yaml(self) -> str:
        body: dict[str, Any] = {
            "schema_version": self.schema_version,
            "group": self.group,
            "display_name": self.display_name,
            "domain": self.domain,
            "lifecycle": self.lifecycle,
            "template_version": self.template_version,
            "tier": self.tier,
            "owner": {"team": self.owner.team, "contact": self.owner.contact},
            "data": {"residency": self.data.residency,
                     "retention_days": self.data.retention_days,
                     "erasure_sla_days": self.data.erasure_sla_days},
            "budget": {"daily_tokens": self.daily_tokens},
            "resources": self.resources,
        }
        return yaml.safe_dump(body, sort_keys=False, width=88)


def manifest_path(root: Path, group: str) -> Path:
    return Path(root) / "groups" / group / MANIFEST


def exists(root: Path, group: str) -> bool:
    return manifest_path(root, group).is_file()


def _int_or_none(raw: Any, field_name: str, group: str) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise GroupError(f"{group}: {field_name} must be a whole number or empty")
    if raw < 0:
        raise GroupError(f"{group}: {field_name} cannot be negative")
    return raw


def load(root: Path, group: str) -> Manifest:
    """The manifest for one group. Every complaint names the group and the key,
    because this is read from hooks and CI where the traceback is all anyone
    sees."""
    path = manifest_path(root, group)
    if not path.is_file():
        raise GroupError(f"{group}: no {MANIFEST} (run `pf bootstrap {group} <project>`)")
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise GroupError(f"{group}: {MANIFEST} does not parse: {exc}") from None
    if not isinstance(raw, dict):
        raise GroupError(f"{group}: {MANIFEST} must be a mapping")

    named = raw.get("group", group)
    if named != group:
        # The directory is the identity the rest of the platform uses; a manifest
        # that disagrees would make every lookup depend on which one was read.
        raise GroupError(f"{group}: {MANIFEST} says group: {named!r}")

    lifecycle = raw.get("lifecycle", "proposed")
    if lifecycle not in LIFECYCLE:
        raise GroupError(f"{group}: lifecycle {lifecycle!r} is not one of "
                         f"{', '.join(LIFECYCLE)}")
    tier = raw.get("tier", "standard")
    if tier not in TIERS:
        raise GroupError(f"{group}: tier {tier!r} is not one of {', '.join(TIERS)}")

    owner_raw = raw.get("owner") or {}
    data_raw = raw.get("data") or {}
    budget_raw = raw.get("budget") or {}
    if not isinstance(owner_raw, dict) or not isinstance(data_raw, dict):
        raise GroupError(f"{group}: owner and data must be mappings")

    return Manifest(
        group=group,
        path=path,
        schema_version=int(raw.get("schema_version", 1) or 1),
        display_name=str(raw.get("display_name", "") or ""),
        domain=str(raw.get("domain", "") or ""),
        lifecycle=lifecycle,
        template_version=int(raw.get("template_version", 0) or 0),
        tier=tier,
        owner=Owner(team=str(owner_raw.get("team", "") or ""),
                    contact=str(owner_raw.get("contact", "") or "")),
        data=DataPolicy(
            residency=str(data_raw.get("residency", "") or ""),
            retention_days=_int_or_none(data_raw.get("retention_days"),
                                        "data.retention_days", group),
            erasure_sla_days=_int_or_none(data_raw.get("erasure_sla_days"),
                                          "data.erasure_sla_days", group),
        ),
        daily_tokens=_int_or_none(budget_raw.get("daily_tokens"),
                                  "budget.daily_tokens", group),
        resources=raw.get("resources") or {},
    )


def save(manifest: Manifest) -> Path:
    """Write the whole manifest. Used when creating one; an *edit* should go
    through `set_key`, which keeps the file's comments."""
    manifest.path.parent.mkdir(parents=True, exist_ok=True)
    manifest.path.write_text(manifest.to_yaml())
    return manifest.path


def set_key(path: Path, key: str, value: Any) -> bool:
    """Replace one top-level scalar in place, preserving everything around it.

    A manifest is hand-owned, and the comments in it are where the reasoning
    lives — why this family's retention is what it is, why the budget was set
    where it was. Round-tripping through the YAML dumper to change one word
    deletes all of that, which is the same reason `gate.yaml` is never rewritten
    by the tool that reads it. So `lifecycle:` and `template_version:` are edited
    as text, and a file that somehow lacks the key falls back to a full dump.
    """
    try:
        lines = path.read_text().splitlines(keepends=True)
    except OSError:
        return False
    rendered = yaml.safe_dump({key: value}, sort_keys=False).strip()
    for i, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            ending = "\n" if line.endswith("\n") else ""
            lines[i] = rendered + ending
            path.write_text("".join(lines))
            return True
    return False


def group_names(root: Path) -> list[str]:
    """Every group directory, manifest or not. Discovery stays a filesystem walk
    so a group that has not been given a manifest yet is still *visible* — being
    unmanaged is a finding, not a reason to disappear."""
    gdir = Path(root) / "groups"
    if not gdir.is_dir():
        return []
    return sorted(p.name for p in gdir.iterdir() if p.is_dir() and not p.name.startswith("."))


def load_all(root: Path) -> list[Manifest]:
    """Every group that has a manifest. Malformed ones raise; the caller is
    always a command that should stop rather than report a partial fleet."""
    return [load(root, g) for g in group_names(root) if exists(root, g)]


def unmanaged(root: Path) -> list[str]:
    return [g for g in group_names(root) if not exists(root, g)]


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, ())


def set_lifecycle(root: Path, group: str, target: str) -> Manifest:
    """Move a group to `target`, or refuse and say what is allowed."""
    if target not in LIFECYCLE:
        raise GroupError(f"{target!r} is not one of {', '.join(LIFECYCLE)}")
    manifest = load(root, group)
    if manifest.lifecycle == target:
        return manifest
    if not can_transition(manifest.lifecycle, target):
        allowed = TRANSITIONS.get(manifest.lifecycle, ())
        raise GroupError(
            f"{group}: {manifest.lifecycle} cannot become {target}"
            + (f"; allowed: {', '.join(allowed)}" if allowed
               else f"; {manifest.lifecycle} is terminal"))
    manifest.lifecycle = target
    if not set_key(manifest.path, "lifecycle", target):
        save(manifest)
    return manifest


def budget_for(root: Path, group: str, default: int) -> int:
    """This family's daily agent-token ceiling. Falls back to the platform
    default when the manifest is absent or silent, so an unmanaged group keeps
    working rather than running with no ceiling at all."""
    try:
        manifest = load(root, group)
    except GroupError:
        return default
    return manifest.daily_tokens if manifest.daily_tokens is not None else default


# --- is this family onboarded? -----------------------------------------------
# `pf align` answers the question per entity: is this company modelled. Nothing
# answered it per family, so a group with no projects passed every gate in the
# repo by having nothing to fail. These checks are the group-level equivalent,
# and their severity is the manifest's lifecycle: a family still being built is
# allowed to be incomplete, one declared live is not.


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # ok | warn | fail
    detail: str
    weight: int = 5

    @property
    def passed(self) -> bool:
        return self.status == "ok"


@dataclass
class GroupReport:
    group: str
    lifecycle: str
    checks: list[Check] = field(default_factory=list)
    error: str = ""  # the manifest itself could not be read

    @property
    def score(self) -> int:
        total = sum(c.weight for c in self.checks)
        if not total:
            return 0
        got = sum(c.weight for c in self.checks if c.passed)
        return round(100 * got / total)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.status == "fail"]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.status == "warn"]

    @property
    def ok(self) -> bool:
        return not self.error and not self.failures


def projects_in(root: Path, group: str) -> list[Path]:
    pdir = Path(root) / "groups" / group / "projects"
    if not pdir.is_dir():
        return []
    return sorted(p for p in pdir.iterdir() if p.is_dir() and not p.name.startswith("."))


def _stub_free(path: Path) -> bool:
    """A scaffolded CLAUDE.md ships its business-rules section as `- (none yet)`.
    Still saying that is the clearest signal a family was created and never
    described."""
    try:
        return "(none yet)" not in path.read_text()
    except OSError:
        return False


def _has_content(d: Path, ignore: set[str]) -> bool:
    if not d.is_dir():
        return False
    return any(p.name not in ignore for p in d.rglob("*") if p.is_file())


def verify(root: Path, group: str) -> GroupReport:
    """Every check a family has to pass to count as onboarded, with the manifest
    deciding whether a shortfall is a warning or an error."""
    root = Path(root)
    gdir = root / "groups" / group
    try:
        manifest = load(root, group)
    except GroupError as exc:
        return GroupReport(group=group, lifecycle="unknown", error=str(exc))

    strict = manifest.strict
    bad = "fail" if strict else "warn"
    checks: list[Check] = []

    def add(name: str, ok: bool, detail: str, weight: int = 5,
            severity: str | None = None) -> None:
        checks.append(Check(name, "ok" if ok else (severity or bad), detail, weight))

    # --- identity
    add("owner recorded", bool(manifest.owner.contact),
        manifest.owner.contact or "no owner.contact: nobody to ask when it breaks",
        weight=10)
    add("archetype recorded", bool(manifest.domain),
        manifest.domain or "no domain: the ontology instance has nothing to agree with")

    instance = gdir / "ontology" / "instance.yaml"
    declared = ""
    if instance.is_file():
        try:
            declared = str((yaml.safe_load(instance.read_text()) or {}).get("domain", "") or "")
        except yaml.YAMLError:
            declared = ""
    add("ontology agrees", bool(declared) and declared == manifest.domain,
        f"instance.yaml domain={declared or 'absent'} vs manifest {manifest.domain or 'absent'}")

    add("template current", not manifest.behind_template,
        f"template_version {manifest.template_version} < {TEMPLATE_VERSION}; "
        "run `pf bootstrap --all`" if manifest.behind_template else
        f"v{manifest.template_version}",
        weight=10, severity="warn")

    # --- the family has members, and they mean something
    projects = projects_in(root, group)
    add("has a project", bool(projects),
        f"{len(projects)} project(s)" if projects
        else "no projects: nothing here can be checked by anything else",
        weight=10)

    unannotated = [p.name for p in projects
                   if not (p / "contracts" / "annotations.yaml").is_file()]
    add("entities annotated", not unannotated,
        "every project annotated" if not unannotated
        else f"no contracts/annotations.yaml: {', '.join(unannotated)}",
        weight=10)

    # --- the family described itself
    add("business rules written", _stub_free(gdir / "CLAUDE.md"),
        "CLAUDE.md still says '(none yet)'" if not _stub_free(gdir / "CLAUDE.md")
        else "described", severity="warn")
    add("group skills", _has_content(gdir / ".claude" / "skills", {"README.md"}),
        "no skills: the group plugin loads and contributes nothing", severity="warn")
    add("group evals", _has_content(gdir / "evals", {"README.md"}),
        "no eval cases for this family's own rules", severity="warn")

    # --- the plumbing bootstrap maintains
    add("loop overrides", (gdir / "loops.yaml").is_file(),
        "no loops.yaml: cannot waive a finding or lower autonomy", weight=3)
    add("plugin manifest",
        (gdir / ".claude" / ".claude-plugin" / "plugin.json").is_file(),
        "no plugin.json: the marketplace lists a plugin that never loads", weight=3)
    add("group card", (gdir / "kg" / "group_card.md").is_file(),
        "no group card: sisters are invisible to each other", weight=3)

    # --- promises that only matter once there is data
    add("retention recorded", manifest.data.retention_days is not None,
        "no data.retention_days: nothing says when this family's data expires",
        weight=3, severity="warn")
    add("erasure deadline recorded", manifest.data.erasure_sla_days is not None,
        "no data.erasure_sla_days: offboarding has no deadline to meet",
        weight=3, severity="warn")

    return GroupReport(group=group, lifecycle=manifest.lifecycle, checks=checks)


def verify_all(root: Path) -> list[GroupReport]:
    out = [verify(root, g) for g in group_names(root) if exists(root, g)]
    for g in unmanaged(root):
        out.append(GroupReport(group=g, lifecycle="unmanaged",
                               error=f"no {MANIFEST}: this group is not managed by "
                                     "the platform (run `pf bootstrap --all`)"))
    return sorted(out, key=lambda r: r.group)
