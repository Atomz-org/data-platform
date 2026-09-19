"""The autonomy ladder, made to move — on evidence, never on a day's enthusiasm.

`LoopSpec.autonomy` is the level a loop was *born* at. This module is the level
it has *earned*. The two are kept apart on purpose: the registry is code and
changes in a pull request, while a promotion is a fact about a track record and
belongs next to the ledger that proves it.

    loop-levels.json        per (loop, project): the effective level and why

## The rules, and why they are these

Promotion is computed from the ledger and the last recorded eval score, and is
never granted by the computation alone — `pf loop promote` prints the evidence
and a human confirms. Demotion *is* automatic, because the signal that earns it
(a patch was reverted) is the one signal a person must not be able to forget to
act on.

    L1 -> L2   >= 20 clean runs in 30 days, 0 errors in the last 10,
               contract evals passing
    L2 -> L3   >= 50 clean runs in 60 days, 0 reverted patches ever at L2,
               live eval pass rate >= 0.95 recorded in the last 14 days

"Clean" is `ok` or `noop`; `proposed` counts as clean only once the proposal
was merged or accepted, because a proposal nobody looked at is not evidence of
anything. `circuit_open` rows are ignored, as in the breaker.

The thresholds are deliberately plain numbers in one place, so that the
question "why is this loop still L1" has an answer that fits on a screen.

## Why a revert drops a level immediately

A reverted patch is the only hard evidence that the loop's judgement was wrong
in a way that reached a human. One such event outweighs any number of quiet
runs, and it resets the clock: the loop must earn the level back from scratch.
`pf loop revert` is how the reverting human tells the ledger; the demotion
follows from the ledger, not from the command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pf.loops.runner import Autonomy, Ledger, LoopSpec

LEVELS: tuple[Autonomy, ...] = ("L1", "L2", "L3")

#: The thresholds. One place, plain numbers.
RULES: dict[str, dict[str, Any]] = {
    "L2": {"clean_runs": 20, "window_days": 30, "recent_errors": 0,
           "recent_n": 10, "evals": "contract"},
    "L3": {"clean_runs": 50, "window_days": 60, "reverts": 0,
           "evals": "live", "live_pass_rate": 0.95, "evals_max_age_days": 14},
}

CLEAN = frozenset({"ok", "noop", "accepted"})
DIRTY = frozenset({"error", "escalated", "reverted", "gate_blocked"})


def levels_path(root: Path) -> Path:
    return root / "loop-levels.json"


def _read(root: Path) -> dict[str, Any]:
    p = levels_path(root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write(root: Path, doc: dict[str, Any]) -> None:
    levels_path(root).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _key(loop: str, project: str) -> str:
    return f"{loop}@{project}"


def effective(root: Path, spec: LoopSpec, project: str) -> Autonomy:
    """The level the runner must honour: the override if one exists, else birth."""
    rec = _read(root).get(_key(spec.name, project))
    if rec and rec.get("level") in LEVELS:
        return rec["level"]
    return spec.autonomy


def set_level(root: Path, spec: LoopSpec, project: str, level: Autonomy, *,
              actor: str, reason: str) -> dict[str, Any]:
    from pf import trace

    previous = effective(root, spec, project)
    doc = _read(root)
    rec = {"level": level, "since": datetime.now(UTC).isoformat(timespec="seconds"),
           "actor": actor, "reason": reason, "born": spec.autonomy}
    doc[_key(spec.name, project)] = rec
    _write(root, doc)
    trace.decision(root, f"level:{spec.name}", project=project, loop=spec.name,
                   from_level=previous, to_level=level, actor=actor, reason=reason)
    return rec


# ------------------------------------------------------------ evidence -----
@dataclass
class Evidence:
    loop: str
    project: str
    current: Autonomy
    target: Autonomy | None
    clean_runs: int = 0
    window_days: int = 0
    recent_errors: int = 0
    reverts: int = 0
    evals_tier: str = ""
    evals_ok: bool | None = None
    evals_pass_rate: float | None = None
    evals_age_days: int | None = None
    blockers: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return self.target is not None and not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def _since(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")


def _rows(ledger: Ledger, loop: str, project: str, days: int) -> list[dict[str, Any]]:
    cutoff = _since(days)
    return [e for e in ledger.read()
            if e["loop"] == loop and e["project"] == project
            and e.get("started_at", "") >= cutoff and e["outcome"] != "circuit_open"]


def latest_evals(root: Path) -> dict[str, Any]:
    """The last recorded eval report, written by `pf evals gate`/`run`."""
    p = root / "data" / "evals" / "latest.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def eligibility(root: Path, spec: LoopSpec, project: str) -> Evidence:
    """What the ledger says about the next rung, and what still blocks it."""
    ledger = Ledger(root)
    cur = effective(root, spec, project)
    idx = LEVELS.index(cur)
    target: Autonomy | None = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None
    ev = Evidence(loop=spec.name, project=project, current=cur, target=target)
    if target is None:
        return ev

    rule = RULES[target]
    rows = _rows(ledger, spec.name, project, rule["window_days"])
    ev.window_days = rule["window_days"]
    ev.clean_runs = sum(1 for e in rows if e["outcome"] in CLEAN)
    ev.reverts = sum(1 for e in ledger.read()
                     if e["loop"] == spec.name and e["project"] == project
                     and e["outcome"] == "reverted")
    if ev.clean_runs < rule["clean_runs"]:
        ev.blockers.append(f"{ev.clean_runs}/{rule['clean_runs']} clean runs "
                           f"in {rule['window_days']}d")

    if "recent_n" in rule:
        recent = [e for e in ledger.recent(spec.name, project, n=rule["recent_n"])
                  if e["outcome"] != "circuit_open"]
        ev.recent_errors = sum(1 for e in recent if e["outcome"] in DIRTY)
        if ev.recent_errors > rule["recent_errors"]:
            ev.blockers.append(f"{ev.recent_errors} failure(s) in the last "
                               f"{rule['recent_n']} runs")
    if "reverts" in rule and ev.reverts > rule["reverts"]:
        ev.blockers.append(f"{ev.reverts} reverted patch(es) on record")

    evals = latest_evals(root)
    ev.evals_tier = rule["evals"]
    tier = evals.get(rule["evals"]) if evals else None
    if not tier:
        ev.evals_ok = None
        ev.blockers.append(f"no {rule['evals']} eval result recorded — "
                           f"run `pf evals-gate{' --live' if rule['evals'] == 'live' else ''}`")
    else:
        ev.evals_ok = bool(tier.get("ok"))
        ev.evals_pass_rate = tier.get("pass_rate")
        when = tier.get("at", "")
        if when:
            try:
                age = datetime.now(UTC) - datetime.fromisoformat(when)
                ev.evals_age_days = age.days
            except ValueError:
                ev.evals_age_days = None
        if not ev.evals_ok:
            ev.blockers.append(f"{rule['evals']} evals failing")
        if "live_pass_rate" in rule and (ev.evals_pass_rate or 0) < rule["live_pass_rate"]:
            ev.blockers.append(f"live pass rate {ev.evals_pass_rate or 0:.2f} "
                               f"< {rule['live_pass_rate']}")
        max_age = rule.get("evals_max_age_days")
        if max_age and (ev.evals_age_days is None or ev.evals_age_days > max_age):
            ev.blockers.append(f"eval result older than {max_age}d")
    return ev


def promote(root: Path, spec: LoopSpec, project: str, *, actor: str,
            force: bool = False) -> tuple[Evidence, dict[str, Any] | None]:
    """Move one rung up. Refuses unless eligible, or `force` with a named actor."""
    ev = eligibility(root, spec, project)
    if ev.target is None:
        return ev, None
    if not ev.eligible and not force:
        return ev, None
    reason = ("forced: " if not ev.eligible else "earned: ") + \
        f"{ev.clean_runs} clean runs/{ev.window_days}d, evals={ev.evals_tier}:{ev.evals_ok}"
    return ev, set_level(root, spec, project, ev.target, actor=actor, reason=reason)


def demote(root: Path, spec: LoopSpec, project: str, *, actor: str,
           reason: str) -> dict[str, Any] | None:
    """Move one rung down. Never below L1."""
    cur = effective(root, spec, project)
    idx = LEVELS.index(cur)
    if idx == 0:
        return None
    return set_level(root, spec, project, LEVELS[idx - 1], actor=actor, reason=reason)


def record_revert(root: Path, spec: LoopSpec, group: str, project: str, *,
                  actor: str, note: str) -> tuple[Any, dict[str, Any] | None]:
    """A human reverted something this loop wrote. Ledger first, then the level.

    The ledger row is the evidence; the demotion is derived from it. Recording
    the revert and forgetting to demote was the failure this ordering prevents.
    """
    import uuid

    from pf import trace
    from pf.loops.runner import LoopRun, _now

    ledger = Ledger(root)
    run = LoopRun(run_id=str(uuid.uuid4())[:8], loop=spec.name, group=group,
                  project=project, started_at=_now(), outcome="reverted",
                  message=f"reverted by {actor}: {note}")
    ledger.append(run)
    trace.decision(root, f"revert:{spec.name}", group=group, project=project,
                   loop=spec.name, actor=actor, note=note, ledger_run=run.run_id)
    rec = demote(root, spec, project, actor=actor,
                 reason=f"patch reverted: {note}")
    return run, rec


def board(root: Path, specs: dict[str, LoopSpec], projects: list[str]) -> list[Evidence]:
    return [eligibility(root, s, p) for s in specs.values() for p in projects]
