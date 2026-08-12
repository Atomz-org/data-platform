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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

Autonomy = Literal["L1", "L2", "L3"]
Outcome = Literal["ok", "noop", "escalated", "circuit_open", "gate_blocked", "error"]

MAX_ATTEMPTS = 3


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Ledger:
    """Append-only run history. The circuit breaker reads it."""

    def __init__(self, root: Path) -> None:
        self.path = root / "loop-ledger.json"

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return []

    def append(self, run: LoopRun) -> None:
        entries = self.read()
        entries.append(run.to_dict())
        self.path.write_text(json.dumps(entries[-500:], indent=2))

    def recent(self, loop: str, project: str, n: int = 5) -> list[dict[str, Any]]:
        return [e for e in self.read()
                if e["loop"] == loop and e["project"] == project][-n:]

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
    daily_budget: int = 200_000,
    dry_run: bool = False,
) -> LoopRun:
    """Execute one loop iteration with state, breaker and ledger around it."""
    from pf import obs

    ledger = Ledger(root)
    breaker = CircuitBreaker(ledger, spec, daily_budget)

    run = LoopRun(run_id=str(uuid.uuid4())[:8], loop=spec.name, group=group,
                  project=project, started_at=_now(),
                  attempt=ledger.consecutive_failures(spec.name, project) + 1)

    allowed, why = breaker.check(group, project)
    if not allowed:
        run.outcome, run.message = "circuit_open", why
        ledger.append(run)
        return run

    if dry_run:
        run.outcome, run.message = "noop", "dry run"
        return run

    from pf.agents.base import reset_spend, spend

    reset_spend()
    t0 = time.time()
    try:
        run.findings = body(run) or []
        run.tokens_used = spend()
        if spec.token_budget and run.tokens_used > spec.token_budget:
            run.message = (f"over budget: {run.tokens_used:,} tokens vs "
                           f"{spec.token_budget:,} allowed — tighten the prompt "
                           f"or lower effort")
        run.outcome = "ok" if run.findings else "noop"
    except Exception as exc:  # a loop must never take the platform down
        run.outcome, run.message = "error", f"{type(exc).__name__}: {exc}"[:400]
    run.duration_ms = int((time.time() - t0) * 1000)

    ledger.append(run)
    obs.record_pipeline_run(group=group, project=project, kind="loop",
                            name=spec.name, status=run.outcome,
                            duration_ms=run.duration_ms,
                            message="; ".join(run.findings)[:900] or run.message)
    return run


def update_state(root: Path, entries: list[str], watch: list[str] | None = None) -> Path:
    """Rewrite STATE.md — the durable spine that outlives any conversation."""
    p = root / "STATE.md"
    lines = [
        "# Loop State — data platform",
        "",
        f"Last run: {_now()}",
        "",
        "## High priority (a loop is acting, or waiting on a human)",
        "",
    ]
    lines += [f"- {e}" for e in entries] or ["- (nothing outstanding)"]
    lines += ["", "## Watch list", ""]
    lines += [f"- {w}" for w in (watch or [])] or ["- (empty)"]
    lines += [
        "",
        "---",
        "Written by `pf loop run`. Cadence, autonomy and budgets live in `LOOP.md`;",
        "binding constraints in `loop-constraints.md`; path policy in `gate.yaml`.",
    ]
    p.write_text("\n".join(lines) + "\n")
    return p
