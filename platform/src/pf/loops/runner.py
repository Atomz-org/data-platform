"""Loop runner: durable state, token budget, circuit breaker, ledger.

Adapted from loop-engineering (vendor/loop-engineering) to a data platform. The
building blocks are theirs; the loops are ours — a data platform's loops watch
freshness, schema drift and metric coverage, not PRs and CI.

Two ideas carry the most weight here:

  * **Autonomy levels.** L1 reports, L2 patches within a gate, L3 runs unattended.
    A loop is promoted only after a track record, never on day one.
  * **The circuit breaker.** A loop that has failed its attempt limit, or spent its
    budget, stops itself. Without it a broken loop burns tokens indefinitely and
    nobody notices until the bill.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

Autonomy = Literal["L1", "L2", "L3"]
Outcome = Literal["ok", "noop", "proposed", "accepted", "reverted", "escalated",
                  "circuit_open", "gate_blocked", "paused", "error"]

MAX_ATTEMPTS = 3
# The platform-wide fallback, used only for a group with no manifest or no
# `budget.daily_tokens`. A managed group gets its own ceiling from `group.yaml`.
DEFAULT_DAILY_BUDGET = 200_000
# Entries kept per ledger file. Now that a file holds one group, this is ~60
# daily sweeps of that family rather than a window other tenants evict.
LEDGER_KEEP = 500


@dataclass
class LoopSpec:
    """A loop definition. The declarative half of LOOP.md."""

    name: str
    description: str
    autonomy: Autonomy
    cadence: str                     # cron-ish, human readable
    token_budget: int                # per run
    scope: str = "project"           # project | group | platform
    writes: bool = False             # does it modify files?
    escalate_after: int = MAX_ATTEMPTS
    #: The highest level this loop may run at, set by a group's loops.yaml
    #: (`pf.loops.config`). A level is earned in the ledger; a group can only
    #: take one away, so an earned L2 under a group ceiling of L1 runs at L1.
    ceiling: Autonomy | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LoopRun:
    """One execution. Appended to the ledger whether it succeeds or not."""

    run_id: str
    loop: str
    group: str
    project: str
    started_at: str
    outcome: Outcome = "ok"
    findings: list[str] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0
    attempt: int = 1
    message: str = ""
    #: The level the run was executed at — earned, not born. See `pf.loops.levels`.
    level: str = ""
    #: Proposals the body made, and what `pf.loops.actions` did with each.
    proposals: list[dict[str, Any]] = field(default_factory=list)
    #: Findings memory dropped, kept for the audit trail but out of STATE.md.
    suppressed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # Bodies call this; the runner executes the queue after the body returns, so
    # a body that raises halfway leaves no half-made branch behind. The queue is
    # not a field: it is transient, and a field would ride into the ledger.
    def propose(self, proposal: Any) -> None:
        self.__dict__.setdefault("_pending", []).append(proposal)

    def pending(self) -> list[Any]:
        return list(self.__dict__.get("_pending") or [])


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Ledger:
    """Append-only run history, one file per group. The circuit breaker reads it.

    It used to be one file for the whole fleet, capped at 500 entries, and both
    halves of that were wrong once there was more than one tenant. A daily sweep
    is 8 loops per project, so at fifty projects the window held less than two
    sweeps: a family's failures were evicted by other families' traffic before
    they could reach the escalation limit, and the breaker un-latched itself,
    silently, by a mechanism that had nothing to do with the loop being fixed.
    The same read also fed `spend_today`, so one tenant's spend closed every
    other tenant's breaker. And because the file is tracked, every loop run in
    any tenant dirtied a file every other tenant's branch also touched.

    Per group, all three go away: the window is that family's own history, spend
    is that family's own spend, and two families never write the same file.

    The fleet-wide file is still *read* for a group's own past entries, so the
    history written before the split is not lost. It is never written again, so
    it ages out on its own rather than needing a migration nobody would run.
    """

    def __init__(self, root: Path, group: str = "") -> None:
        self.root = Path(root)
        self.group = group
        self.path = (self.root / "groups" / group / "loop-ledger.json" if group
                     else self.root / "loop-ledger.json")
        self.legacy = self.root / "loop-ledger.json" if group else None

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def read(self) -> list[dict[str, Any]]:
        """This group's history, oldest first: what the shared file still holds
        for it, then its own."""
        own = self._load(self.path)
        if self.legacy is None or self.legacy == self.path:
            return own
        return [e for e in self._load(self.legacy)
                if e.get("group") == self.group] + own

    def append(self, run: LoopRun) -> None:
        # Its own file only. Reading the union here would copy the shared file's
        # rows into the group's on the first append and double every count.
        entries = self._load(self.path)
        entries.append(run.to_dict())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries[-LEDGER_KEEP:], indent=2), encoding="utf-8")

    def recent(self, loop: str, project: str, n: int = 5) -> list[dict[str, Any]]:
        # `group` is filtered as well as `project` because the shared file holds
        # every tenant's rows, and two families following the house `<group>-<region>`
        # convention are one renamed project away from colliding on slug alone.
        return [e for e in self.read()
                if e["loop"] == loop and e["project"] == project
                and (not self.group or e.get("group") == self.group)][-n:]

    def consecutive_failures(self, loop: str, project: str) -> int:
        """Failures since the last clean run, ignoring the breaker's own records.

        `circuit_open` entries are skipped rather than counted or treated as a
        clean run. Counting them as clean let the breaker un-latch: it tripped,
        wrote one `circuit_open` row, and the very next invocation saw a
        non-failure at the head of the streak and ran the broken body again.
        Skipping them means the breaker stays open until a human clears it with
        `pf loop reset` — which is the point of a breaker.
        """
        count = 0
        for e in reversed(self.recent(loop, project, n=20)):
            outcome = e["outcome"]
            if outcome == "circuit_open":
                continue
            if outcome in ("error", "escalated"):
                count += 1
            else:
                break
        return count

    def reset(self, loop: str, group: str, project: str, note: str = "") -> LoopRun:
        """Clear a latched breaker by appending a clean marker.

        The ledger is append-only on purpose — the history of a loop that had to
        be reset is itself worth keeping — so this records the reset rather than
        deleting the failures.
        """
        run = LoopRun(run_id=str(uuid.uuid4())[:8], loop=loop, group=group,
                      project=project, started_at=_now(), outcome="noop",
                      message=f"manual reset: {note}" if note else "manual reset")
        self.append(run)
        return run

    def spend_today(self) -> int:
        today = _now()[:10]
        return sum(e.get("tokens_used", 0) for e in self.read()
                   if e.get("started_at", "").startswith(today))


def all_entries(root: Path) -> list[dict[str, Any]]:
    """Every group's history as one timeline, for the fleet-wide views.

    A group's own `read()` already folds in the rows the shared file still holds
    for it, so unioning those covers everything except rows belonging to a group
    whose directory is gone. Those are a departed tenant's history and are
    included too: a run that happened is a run that happened, and hiding it
    would make the fleet's success ratio flatter than the truth.
    """
    from pf.groups import group_names

    names = group_names(root)
    out: list[dict[str, Any]] = []
    for g in names:
        out += Ledger(root, g).read()
    out += [e for e in Ledger._load(Path(root) / "loop-ledger.json")
            if e.get("group") not in set(names)]
    return sorted(out, key=lambda e: e.get("started_at", ""))


class CircuitBreaker:
    """Stops a loop that is failing or over budget.

    The failure mode this prevents is specific: a loop whose fix does not work
    retries forever, spending tokens on the same broken change. Attempts are
    counted in the ledger, not in memory, so a restart does not reset them.
    """

    def __init__(self, ledger: Ledger, spec: LoopSpec, daily_budget: int) -> None:
        self.ledger = ledger
        self.spec = spec
        self.daily_budget = daily_budget

    def check(self, group: str, project: str) -> tuple[bool, str]:
        fails = self.ledger.consecutive_failures(self.spec.name, project)
        if fails >= self.spec.escalate_after:
            return False, (f"circuit open: {fails} consecutive failures "
                           f"(limit {self.spec.escalate_after}). Escalate to a human; "
                           f"clear by resolving the finding, not by retrying.")
        spent = self.ledger.spend_today()
        if self.daily_budget and spent >= self.daily_budget:
            return False, (f"circuit open: {spent:,} tokens spent today "
                           f"exceeds the {self.daily_budget:,} daily budget")
        return True, ""


def run_loop(
    spec: LoopSpec,
    body: Callable[[LoopRun], list[str]],
    *,
    root: Path,
    group: str,
    project: str,
    daily_budget: int | None = None,
    dry_run: bool = False,
) -> LoopRun:
    """Execute one loop iteration with state, breaker and ledger around it.

    `daily_budget` defaults to this family's own ceiling from `group.yaml`, not
    to a fleet-wide number: a shared ceiling means the tenant whose loops run
    first each day spends it, and the rest are refused for reasons that have
    nothing to do with them. A group with no manifest keeps the platform default,
    so an unmanaged group still runs.
    """
    from pf import groups, obs, trace
    from pf.loops import levels, memory

    ledger = Ledger(root, group)
    if daily_budget is None:
        daily_budget = groups.budget_for(root, group, DEFAULT_DAILY_BUDGET)

    # A family that is suspended, still being provisioned, or on its way out
    # does not run loops. The manifest is the only place that decision is
    # recorded, and a group without one is legacy rather than paused.
    try:
        manifest = groups.load(root, group)
    except groups.GroupError:
        manifest = None
    if manifest is not None and not manifest.runs_loops:
        paused = LoopRun(run_id=str(uuid.uuid4())[:8], loop=spec.name, group=group,
                         project=project, started_at=_now(), outcome="paused",
                         message=f"group is {manifest.lifecycle}; loops run when it is active")
        ledger.append(paused)
        return paused

    breaker = CircuitBreaker(ledger, spec, daily_budget)
    level = levels.effective(root, spec, project)
    tr = trace.start(root, "loop", spec.name, group=group, project=project)
    tr.intent(spec.description, loop=spec.name, born=spec.autonomy, earned=level,
              budget=spec.token_budget, cadence=spec.cadence, dry_run=dry_run)

    run = LoopRun(run_id=str(uuid.uuid4())[:8], loop=spec.name, group=group,
                  project=project, started_at=_now(),
                  attempt=ledger.consecutive_failures(spec.name, project) + 1,
                  level=level)

    allowed, why = breaker.check(group, project)
    tr.step("circuit_breaker", "open" if not allowed else "closed", attempt=run.attempt,
            detail=why)
    if not allowed:
        run.outcome, run.message = "circuit_open", why
        ledger.append(run)
        tr.close(run.outcome, message=why)
        return run

    if dry_run:
        run.outcome, run.message = "noop", "dry run"
        tr.close(run.outcome, message="dry run")
        return run

    from pf.agents.base import reset_spend, spend

    reset_spend()
    t0 = time.time()
    pdir = root / "groups" / group / "projects" / project
    token = trace._current.set(tr)
    try:
        raw = body(run) or []
        tr.step("body", findings=len(raw), proposals=len(run.pending()))
        run.tokens_used = spend()
        if spec.token_budget and run.tokens_used > spec.token_budget:
            run.message = (f"over budget: {run.tokens_used:,} tokens vs "
                           f"{spec.token_budget:,} allowed — tighten the prompt "
                           f"or lower effort")

        # Memory before the ledger: a suppressed finding is a decision already
        # made, and re-recording it every run is how STATE.md stops being read.
        applied = memory.apply(pdir, spec.name, list(raw)) if pdir.exists() \
            else memory.Applied(kept=list(raw))
        run.findings = applied.kept
        run.suppressed = [f for f, _ in applied.suppressed]
        tr.step("memory", kept=len(run.findings), suppressed=len(run.suppressed),
                annotated=len(applied.annotated),
                suppressed_by=[e.id for _, e in applied.suppressed])
        for f in run.findings:
            tr.finding(f)

        # Then the proposals, at the level the loop has earned. `execute` is
        # what decides whether "earned" means a record or a pull request.
        from pf.loops import actions
        for proposal in run.pending():
            out = actions.execute(root, group, project, proposal, level=level,
                                  dry_run=dry_run)
            run.proposals.append(out.to_dict())
            tr.proposal(proposal, out)
        statuses = {o["status"] for o in run.proposals}
        if statuses & {"proposed", "branched", "recorded"}:
            run.outcome = "proposed"
        elif "gate_blocked" in statuses:
            run.outcome = "gate_blocked"
            run.message = "; ".join(o["message"] for o in run.proposals
                                    if o["status"] == "gate_blocked")[:400]
        elif "error" in statuses:
            run.outcome = "error"
            run.message = "; ".join(o["message"] for o in run.proposals
                                    if o["status"] == "error")[:400]
        else:
            run.outcome = "ok" if run.findings else "noop"
    except Exception as exc:  # a loop must never take the platform down
        run.outcome, run.message = "error", f"{type(exc).__name__}: {exc}"[:400]
        tr.error(exc, step="body")
    finally:
        trace._current.reset(token)
    run.duration_ms = int((time.time() - t0) * 1000)

    ledger.append(run)
    tr.close(run.outcome, message=run.message, tokens=run.tokens_used,
             ms=run.duration_ms, ledger=str(ledger.path.name))
    obs.record_pipeline_run(group=group, project=project, kind="loop",
                            name=spec.name, status=run.outcome,
                            duration_ms=run.duration_ms,
                            message="; ".join(run.findings)[:900] or run.message)
    return run


_STATE_TITLE = "# Loop State — data platform"
_STATE_HIGH = "## High priority (a loop is acting, or waiting on a human)"
_STATE_WATCH = "## Watch list"
_STATE_EMPTY = "- (nothing outstanding)"
_STATE_FOOTER = (
    "---",
    "Written by `pf loop run`. Cadence, autonomy and budgets live in `LOOP.md`;",
    "binding constraints in `loop-constraints.md`; path policy in `gate.yaml`.",
)


def _state_sections(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """Read the high-priority block of an existing STATE.md back into its parts:
    the unscoped bullets that precede any heading, and one bullet list per
    `### group/project` heading, in file order. Everything else in the file is
    regenerated, so nothing else is parsed."""
    legacy: list[str] = []
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith("## High priority")
            current = None
            continue
        if not inside:
            continue
        if line.startswith("### "):
            current = sections.setdefault(line[4:].strip(), [])
        elif line.startswith("- ") and line != _STATE_EMPTY:
            (legacy if current is None else current).append(line[2:])
    return legacy, sections


def update_state(root: Path, entries: list[str], watch: list[str] | None = None,
                 *, group: str = "", project: str = "", writer: str = "") -> Path:
    """Write STATE.md — the durable spine that outlives any conversation.

    One section per project, so the file holds the whole platform's position
    and not just the last project that ran. Before this, every run rewrote the
    file wholesale: with three groups, `pf loop run-all` on one erased the open
    findings of the other two, and the spine was one project deep.

    Format::

        # Loop State — data platform

        Last run: <timestamp>

        ## High priority (a loop is acting, or waiting on a human)

        - <an unscoped bullet, from a write with no group/project>

        ### <group>/<project> · <writer>

        - <this project's open findings>

        ## Watch list

        - <loops above L1, or (empty)>

        ---
        <footer>

    A scoped write (`group` and `project` both given) replaces only its own
    `###` section, removes it when `entries` is empty, and keeps every other
    section and every unscoped bullet verbatim. `writer` names the command
    behind the section (`loops`, `onboarding`): `pf loop run-all` and
    `pf align status --state` both write for one project, and with a single
    section per project a clean run-all deleted the ladder position written
    moments before. The `Last run:` line and the watch list are rewritten on
    every call — the watch list is a platform fact, not a per-project one, so
    every caller passes `registry.watch_list()`. An unscoped write keeps the
    old behaviour: it rewrites the whole block, sections included.
    """
    if bool(group) != bool(project):
        raise ValueError("update_state: scope needs both group and project, or neither")
    # One physical line per bullet. A dbt Database Error is a header plus
    # indented lines, and the read-back above keeps `- ` lines only: written
    # intact, such a finding lost its tail on the next project's write.
    entries = [" ".join(e.split()) for e in entries]
    p = root / "STATE.md"
    legacy, sections = _state_sections(p.read_text()) if p.exists() else ([], {})
    if group:
        key = f"{group}/{project}" + (f" · {writer}" if writer else "")
        if entries:
            sections[key] = list(entries)
        else:
            sections.pop(key, None)
    else:
        legacy, sections = list(entries), {}

    lines = [_STATE_TITLE, "", f"Last run: {_now()}", "", _STATE_HIGH, ""]
    if legacy:
        lines += [f"- {e}" for e in legacy] + [""]
    for key, items in sections.items():
        lines += [f"### {key}", ""] + [f"- {e}" for e in items] + [""]
    if not legacy and not sections:
        lines += [_STATE_EMPTY, ""]
    lines += [_STATE_WATCH, ""]
    lines += [f"- {w}" for w in (watch or [])] or ["- (empty)"]
    lines += ["", *_STATE_FOOTER]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p
