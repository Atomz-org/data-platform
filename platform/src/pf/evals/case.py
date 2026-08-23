"""Loading eval cases off disk.

The on-disk shape is the one every scaffolded project's README has documented
since the beginning — one JSON object per case, with `name`, `input` and
`expect`. That format is kept exactly, because changing it would silently
invalidate cases people have already written against the documented contract.

What is added around it is metadata that an eval corpus needs to stay useful:
`agent` (which step this case exercises), `why` (the reason the case exists, so
a future reader can tell a deliberate assertion from an arbitrary one) and
`tags` for selection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Which agent a case drives, and the `input` keys that agent's callable takes.
# A case naming an agent that is not here is rejected at load rather than at
# call time — a typo in a corpus of 40 cases should not cost an API round trip
# to find.
AGENT_INPUTS: dict[str, tuple[str, ...]] = {
    "test_failure_triage": ("failures", "lineage"),
    "freshness_triage": ("monitor_rows",),
    "metric_gap_proposer": ("gaps", "mart_detail"),
}


class CaseError(ValueError):
    """A case file that cannot be loaded or does not describe a runnable case."""


@dataclass(frozen=True)
class Case:
    """One eval case: an input to an agent and what must be true of the output."""

    name: str
    agent: str
    input: dict[str, Any]
    expect: dict[str, Any]
    why: str = ""
    tags: tuple[str, ...] = ()
    source: Path | None = None
    # Which tier the case came from — see `discover`. Reported per tier, because
    # a failing platform case and a failing project case mean different things
    # and are fixed by different people.
    scope: str = "platform"
    # For platform cases, the toolkit that owns the feature under test.
    owner: str = ""

    @property
    def qualified_name(self) -> str:
        return f"{self.agent}/{self.name}"


def load_case(path: Path, scope: str = "platform", owner: str = "") -> Case:
    """Parse and validate one case file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CaseError(f"{path}: not valid JSON — {exc}") from exc
    return validate_case(raw, origin=str(path), scope=scope, owner=owner)


def validate_case(raw: Any, origin: str, scope: str = "platform",
                  owner: str = "") -> Case:
    """Validate a case object, wherever it came from.

    Split out from `load_case` so a freshly rendered template can be checked
    *before* it is written. A generator that wrote invalid cases and discovered
    it on the next run would leave the project in a state where `pf evals` fails
    on files the project never authored.
    """
    path = origin

    if not isinstance(raw, dict):
        raise CaseError(f"{path}: expected a JSON object, got {type(raw).__name__}")

    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise CaseError(f"{path}: missing a string 'name'")

    agent = raw.get("agent")
    if agent not in AGENT_INPUTS:
        raise CaseError(
            f"{path}: 'agent' must be one of {', '.join(sorted(AGENT_INPUTS))}, "
            f"got {agent!r}")

    inputs = raw.get("input")
    if not isinstance(inputs, dict):
        raise CaseError(f"{path}: 'input' must be an object")

    # Every key the agent takes must be present. A case missing `lineage` would
    # otherwise run with an empty neighbourhood and grade a question the agent
    # was never actually asked.
    required = set(AGENT_INPUTS[agent])
    missing = required - set(inputs)
    if missing:
        raise CaseError(
            f"{path}: agent '{agent}' needs input keys {sorted(missing)}")
    unknown = set(inputs) - required
    if unknown:
        raise CaseError(
            f"{path}: agent '{agent}' takes no input {sorted(unknown)} "
            f"(known: {sorted(required)})")

    expect = raw.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise CaseError(f"{path}: 'expect' must be a non-empty object")

    return Case(
        name=name,
        agent=agent,
        input=inputs,
        expect=expect,
        why=raw.get("why", ""),
        tags=tuple(raw.get("tags", ())),
        source=Path(origin),
        scope=scope,
        owner=owner,
    )


# Where each tier keeps its cases, in the order they run.
PLATFORM_EVALS = "platform/toolkits/*/evals"
GROUP_EVALS = "evals"
PROJECT_EVALS = "evals/cases"


def discover(root: Path, group: str | None = None, project: str | None = None,
             agents: set[str] | None = None,
             tags: set[str] | None = None,
             scopes: set[str] | None = None) -> list[Case]:
    """Collect cases from the three tiers, outermost first.

    **platform** — `platform/toolkits/<toolkit>/evals/`. Each toolkit owns the
    evals for the feature it ships, next to the skills that describe it, so a
    toolkit is a self-contained unit: what it does, how to do it, and the proof
    it still works. These check platform features and health and are true for
    every entity.

    **group** — `groups/<group>/evals/`. What is shared across sisters and only
    across sisters: the group's ontology instance, its conformed dimensions, its
    group-level metrics.

    **project** — `groups/<group>/projects/<project>/evals/cases/`. One entity's
    business logic.

    The walk is strictly downward. It reads the named group and the named project
    and nothing else — never a sister, never another group. A corpus that pulled
    in a sister's cases would assert one company's business rules against
    another's agent, which is the bug this platform is organised to prevent.
    """
    cases: list[Case] = []
    want = scopes or {"platform", "group", "project"}

    if "platform" in want:
        for tdir in sorted((root / "platform" / "toolkits").glob("*/evals")):
            for path in sorted(tdir.rglob("*.json")):
                # `templates/` holds parameterised shapes, not runnable cases —
                # they carry `{{bindings}}` where the nouns go and are rendered
                # into a project by `pf evals-gen`.
                if "templates" in path.relative_to(tdir).parts:
                    continue
                cases.append(load_case(path, scope="platform",
                                       owner=tdir.parent.name))

    if "group" in want and group:
        for path in sorted((root / "groups" / group / GROUP_EVALS).rglob("*.json")):
            cases.append(load_case(path, scope="group", owner=group))

    if "project" in want and group and project:
        pdir = root / "groups" / group / "projects" / project
        for path in sorted((pdir / PROJECT_EVALS).rglob("*.json")):
            cases.append(load_case(path, scope="project", owner=f"{group}/{project}"))

    if agents:
        cases = [c for c in cases if c.agent in agents]
    if tags:
        cases = [c for c in cases if tags & set(c.tags)]

    _reject_duplicates(cases)
    return cases


def _reject_duplicates(cases: list[Case]) -> None:
    """Two cases with the same qualified name make a report ambiguous.

    The likely cause is a group or project copying a platform case to tweak it
    rather than changing the platform one. Both then run, and if the tweak
    reversed an expectation the suite reports a contradiction as a failure.

    Each tier tests something the others do not, so a name that appears twice is
    a sign the tiers have been confused rather than a deliberate override.
    """
    seen: dict[str, Path | None] = {}
    for c in cases:
        if c.qualified_name in seen:
            raise CaseError(
                f"duplicate case '{c.qualified_name}' in {c.source} — already "
                f"defined by {seen[c.qualified_name]}. Rename it, or change the "
                f"platform case if the platform expectation is the wrong one.")
        seen[c.qualified_name] = c.source
