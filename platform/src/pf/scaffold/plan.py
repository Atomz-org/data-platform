"""What `pf new-project` would do, before it does it.

Scaffolding is cheap to run and expensive to run *wrong*: a project created with
the wrong capability set has to be found later, and `pf bootstrap` can only
backfill what is missing — it will not remove what should never have been added.
So the decision comes first, and this is the surface it is made on.

It is also the token-optimised path, which is the reason it exists in this shape
rather than as prose in a skill. An agent deciding how to scaffold used to have
to discover the answers: read `pf.capabilities` for the registry, read
`pf.runtime.targets` for the warehouses, check whether the group existed, guess
whether the directory was already taken. Six or seven tool calls returning whole
files, to answer questions with fixed short answers.

`pf new-project --plan` answers all of them in one call and about thirty lines.
Nothing here writes; nothing here needs the agent to read a file afterwards.

The blockers are the point. A plan that lists what *would* happen but not what
would *stop* it is a plan you still have to try before you trust.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pf.capabilities import Capability, gate_additions, missing_env


@dataclass
class Plan:
    """A scaffold, resolved but not performed."""

    group: str
    project: str
    root: Path
    caps: list[Capability] = field(default_factory=list)
    #: Reasons this scaffold would fail or do damage. Non-empty means stop.
    blockers: list[str] = field(default_factory=list)
    #: Reasons to look before proceeding. Non-empty is fine to proceed through.
    warnings: list[str] = field(default_factory=list)
    is_rollup: bool = False

    @property
    def project_dir(self) -> Path:
        return self.root / "groups" / self.group / "projects" / self.project

    @property
    def ok(self) -> bool:
        return not self.blockers


def build(root: Path, group: str, project: str, caps: list[Capability],
          is_rollup: bool = False) -> Plan:
    """Resolve a scaffold against the repository as it stands.

    Every check here is one an agent would otherwise perform by reading files,
    and two of them are the failures that actually happen: scaffolding into a
    directory that already holds a project, and scaffolding a sister into a
    group that does not exist yet.
    """
    p = Plan(group=group, project=project, root=Path(root), caps=list(caps),
             is_rollup=is_rollup)

    if not (p.root / "groups" / group).is_dir():
        p.blockers.append(
            f"group '{group}' does not exist — run `pf new-group {group}` first")

    if p.project_dir.exists():
        existing = sum(1 for _ in p.project_dir.rglob("*") if _.is_file())
        p.blockers.append(
            f"{p.project_dir.relative_to(p.root)} already exists ({existing} file(s)). "
            f"To add a capability to it use `pf capability-add`; to bring it up to "
            f"the current platform use `pf bootstrap {group} {project}`")

    # A rollup reads its sisters, so a group with none is a rollup over nothing.
    if is_rollup:
        sisters = [
            d.name for d in (p.root / "groups" / group / "projects").iterdir()
            if d.is_dir() and not d.name.endswith("-rollup")
        ] if (p.root / "groups" / group / "projects").is_dir() else []
        if not sisters:
            p.warnings.append(
                f"group '{group}' has no sister projects yet, so this roll-up will "
                f"union nothing until one is created")

    # Missing credentials do not block: the scaffold is inert without them and
    # `pf doctor` reports them later. They are worth seeing now because the
    # cheapest moment to pick a different warehouse is before the files exist.
    for cap, names in missing_env(p.caps).items():
        p.warnings.append(f"capability '{cap}' needs unset env: {', '.join(names)}")

    return p


def render(p: Plan) -> str:
    """The plan, compact enough that reading it is cheaper than exploring."""
    lines = [f"plan: {p.group}/{p.project}" + ("  (roll-up)" if p.is_rollup else "")]
    lines.append(f"  path       {p.project_dir.relative_to(p.root)}")

    if p.caps:
        lines.append(f"  enabling   {len(p.caps)} capability(ies)")
        for c in sorted(p.caps, key=lambda x: x.name):
            bits = []
            if c.files:
                bits.append(f"{len(c.files)} file(s)")
            if c.ci_jobs:
                bits.append("ci: " + ", ".join(sorted(c.ci_jobs)))
            if c.env:
                bits.append("env: " + ", ".join(c.env))
            lines.append(f"    {c.name:14} {' · '.join(bits) or '—'}")
    else:
        lines.append("  enabling   nothing (--without removed every default)")

    rules = gate_additions(p.caps)
    n_rules = sum(len(v) for v in rules.values())
    if n_rules:
        lines.append(f"  gate       +{n_rules} rule(s): "
                     + ", ".join(f"{k} ×{len(v)}" for k, v in sorted(rules.items())))

    jobs = sorted({j for c in p.caps for j in c.ci_jobs})
    lines.append(f"  ci         {', '.join(jobs) if jobs else 'no jobs — no CI workflow'}")

    for w in p.warnings:
        lines.append(f"  [!]        {w}")
    for b in p.blockers:
        lines.append(f"  BLOCKED    {b}")

    if p.ok:
        lines.append("")
        lines.append("  apply with the same command minus --plan")
    return "\n".join(lines)
