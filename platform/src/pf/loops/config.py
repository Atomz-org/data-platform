"""What a group changes about the loop catalogue — declared once, per family.

`registry.py` answers "what loops exist". This answers "what does *this* group
run, at what cadence, with what suppressed", and the two are deliberately
different questions: the registry is platform code and the same for every
company, while a family of commodity desks and a family of SaaS entities do not
want the same loops at the same cadence.

## Why the group and not the project

A loop watches the family's subjects once: freshness of the feeds every sister
ingests, PII in the marts every sister builds, the graph every sister indexes.
Deciding "pii-audit runs daily" per entity would be the same decision restated
per sister, and the first time a sister forgot to restate it the family would
have an ungoverned member. So cadence, budget, autonomy and waivers are the
group's, and a project does not get a `loops.yaml` at all.

A project's *own* knowledge still reaches a loop — through its `CLAUDE.md`, which
`pf.agents.base.cached_prefix` puts in front of every LLM-backed loop. "Futures
do not settle at weekends" is a project rule that changes what freshness-triage
concludes; it is not a loop setting, so it does not live here.

## What an override may and may not do

It may *lower* a loop's autonomy (L2 -> L1) and never raise it. Promotion is a
human decision made in the registry after a ledger track record, and a YAML file
that could grant L3 would be a way around the only thing that keeps autonomy
honest. Lowering is refused for a loop that writes: L1 means "writes nothing",
and a lowered `index-refresher` would still rebuild the graph, only now inside
the `pf loop run-all` sweep that is documented as read-only. Disable such a
loop instead. It may disable a loop, with a reason that `pf loop list --group` shows,
so a switched-off monitor is visible rather than quietly absent. It may waive a
finding, with a reason, because a monitor that always warns and is never acted
on is worse than no monitor — and a waiver with no reason is that same failure
wearing a different hat.

An unknown loop name or an unknown key is refused rather than ignored. A typo
that silently does nothing is the failure mode this file exists to prevent.

## Schema: groups/<group>/loops.yaml

    version: 1
    loops:
      <loop-name>:            # one of the 8 registry names
        enabled: true|false   # default true; a `reason:` beside enabled: false is shown by `pf loop list --group`
        reason: "<why disabled>"
        cadence: "<free text>"
        token_budget: <non-negative int>
        autonomy: L1          # may only LOWER the registry level (L2 -> L1), and never a loop that writes
        waivers:              # findings to suppress; reason is mandatory
          - node: "rpt_*"     # a node *name* or fnmatch glob; for pii-audit use model.column
            reason: "..."
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from pf.loops.runner import LoopSpec

CONFIG_NAME = "loops.yaml"

#: Autonomy in ascending order. An override may move a loop left, never right.
LEVELS = ("L1", "L2", "L3")

_KEYS = ("enabled", "reason", "cadence", "token_budget", "autonomy", "waivers")


class LoopConfigError(ValueError):
    """A loops.yaml that says something the platform will not do."""


@dataclass(frozen=True)
class Waiver:
    """One suppressed finding. The reason is the whole point of writing it down."""

    node: str
    reason: str

    def __post_init__(self) -> None:
        if not self.node or not str(self.node).strip():
            raise LoopConfigError("a waiver needs a `node:` name or glob")
        if not self.reason or not str(self.reason).strip():
            raise LoopConfigError(
                f"waiver for `{self.node}` has no reason. A silenced finding with no "
                f"stated reason is a monitor nobody acts on — say why it is safe")


@dataclass(frozen=True)
class LoopOverride:
    """One loop's group-level settings. `None` means the registry value stands."""

    enabled: bool = True
    reason: str = ""
    cadence: str | None = None
    token_budget: int | None = None
    autonomy: str | None = None
    waivers: tuple[Waiver, ...] = ()

    @property
    def touches_spec(self) -> bool:
        """Whether the effective spec differs from the registry's, for the
        `source` column: waivers alone leave the spec itself untouched."""
        return any(v is not None for v in (self.cadence, self.token_budget,
                                            self.autonomy))


# ------------------------------------------------------------------- read --
def _specs() -> dict[str, LoopSpec]:
    """Every loop a group may configure: the registry's and the tools'."""
    from pf.loops.registry import all_specs
    return all_specs()


def config_path(root: Path, group: str) -> Path:
    return Path(root) / "groups" / group / CONFIG_NAME


def load(path: Path) -> dict[str, Any]:
    """One loops.yaml's `loops:` mapping, or an empty one. A missing file is
    not an error — a group with nothing to change runs the registry as is."""
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    if not isinstance(doc, dict):
        raise LoopConfigError(f"{path}: expected a mapping with a `loops:` key")
    loops = doc.get("loops") or {}
    if not isinstance(loops, dict):
        raise LoopConfigError(f"{path}: `loops:` must be a mapping of loop name to settings")
    return loops


def overrides(root: Path, group: str) -> dict[str, LoopOverride]:
    """Parse and validate the group's overrides, keyed by loop name."""
    path = config_path(root, group)
    out: dict[str, LoopOverride] = {}
    specs = _specs()
    for name, raw in load(path).items():
        spec = specs.get(name)
        if spec is None:
            raise LoopConfigError(
                f"{path}: unknown loop `{name}`. Known loops: {', '.join(specs)}")
        out[name] = _parse(path, spec, raw or {})
    return out


def _parse(path: Path, spec: LoopSpec, raw: Any) -> LoopOverride:
    where = f"{path}: `{spec.name}`"
    if not isinstance(raw, dict):
        raise LoopConfigError(f"{where} must be a mapping, not {type(raw).__name__}")
    unknown = sorted(set(raw) - set(_KEYS))
    if unknown:
        raise LoopConfigError(f"{where}: unknown key(s) {', '.join(unknown)}. "
                              f"Allowed: {', '.join(_KEYS)}")

    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise LoopConfigError(f"{where}: `enabled` must be true or false")

    cadence = raw.get("cadence")
    if cadence is not None and not isinstance(cadence, str):
        raise LoopConfigError(f"{where}: `cadence` is free text, got {cadence!r}")

    budget = raw.get("token_budget")
    # bool is an int in Python; `token_budget: true` must not read as 1.
    if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int)
                               or budget < 0):
        raise LoopConfigError(f"{where}: `token_budget` must be a non-negative "
                              f"integer, got {budget!r}")

    autonomy = raw.get("autonomy")
    if autonomy is not None:
        if autonomy not in LEVELS:
            raise LoopConfigError(f"{where}: `autonomy` must be one of "
                                  f"{', '.join(LEVELS)}, got {autonomy!r}")
        if LEVELS.index(autonomy) > LEVELS.index(spec.autonomy):
            raise LoopConfigError(
                f"{where}: cannot raise autonomy from {spec.autonomy} to {autonomy}. "
                f"A group may only lower it; promotion is a human decision made in "
                f"the registry after a ledger track record")
        if LEVELS.index(autonomy) < LEVELS.index(spec.autonomy) and spec.writes:
            raise LoopConfigError(
                f"{where}: cannot lower autonomy to {autonomy}: this loop writes, and "
                f"L1 means writes nothing. Lowering would only relabel it and put it "
                f"in the read-only `pf loop run-all` sweep; set `enabled: false` with "
                f"a reason instead")

    raw_waivers = raw.get("waivers") or []
    if not isinstance(raw_waivers, list):
        raise LoopConfigError(f"{where}: `waivers` must be a list")
    waivers = []
    for w in raw_waivers:
        if not isinstance(w, dict):
            raise LoopConfigError(f"{where}: each waiver needs `node:` and `reason:`")
        waivers.append(Waiver(node=str(w.get("node") or ""),
                              reason=str(w.get("reason") or "")))

    return LoopOverride(enabled=enabled, reason=str(raw.get("reason") or ""),
                        cadence=cadence, token_budget=budget, autonomy=autonomy,
                        waivers=tuple(waivers))


# ---------------------------------------------------------------- resolve --
def resolve(root: Path, group: str) -> dict[str, LoopSpec]:
    """The loops this group runs, in registry order, with its overrides applied.

    Disabled loops are absent rather than flagged, so a caller iterating the
    result cannot run one by forgetting to check. `disabled()` is where they
    went.
    """
    ov = overrides(root, group)
    out: dict[str, LoopSpec] = {}
    for name, spec in _specs().items():
        o = ov.get(name)
        if o is None:
            out[name] = spec
            continue
        if not o.enabled:
            continue
        # Lowering autonomy sets the ceiling too: the born level alone would not
        # hold a loop that has since earned a higher one in the ledger.
        changes = {k: v for k, v in (("cadence", o.cadence),
                                     ("token_budget", o.token_budget),
                                     ("autonomy", o.autonomy),
                                     ("ceiling", o.autonomy)) if v is not None}
        out[name] = replace(spec, **changes) if changes else spec
    return out


def disabled(root: Path, group: str) -> dict[str, str]:
    """Loop -> why it is off. The yaml's own words when it gave any."""
    return {name: o.reason or f"disabled in groups/{group}/{CONFIG_NAME}"
            for name, o in overrides(root, group).items() if not o.enabled}


def waivers(root: Path, group: str, loop: str) -> tuple[Waiver, ...]:
    o = overrides(root, group).get(loop)
    return o.waivers if o else ()


def waived(name: str, waivers: tuple[Waiver, ...]) -> Waiver | None:
    """The waiver covering `name`, or None. Case-sensitive glob, as dbt names are."""
    for w in waivers:
        if fnmatch.fnmatchcase(name, w.node):
            return w
    return None
