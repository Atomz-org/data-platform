"""The circuit breaker, with the ledger as its only memory.

The loop runner keeps its breaker count in `loop-ledger.json`. This one keeps
nothing: consecutive validation failures are *read from the provenance chain*,
because the chain already records every rejection with its reason and cannot
be edited — so the count cannot be reset by deleting a file, and a restart
cannot forget it. That is the property AGENTS.md asks of session state: it
lives in the record of what happened, not in a scratch file beside it.

    open   after `max_consecutive_validation_failures` REJECT executions for
           this entity with no PASS between them
    closed by a PASS, or by `pf govern breaker reset --reason`, which writes a
           clean marker to the chain with the reason and the actor

CIRCUIT_BROKEN records — the breaker refusing work — are skipped when counting,
so the breaker cannot unlatch itself by being consulted. ESCALATED (held for a
person) is neither a failure nor a success and is skipped too.

The per-invocation iteration budget is in-process on purpose: it bounds one
run of one engine, and a run does not survive a restart.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pf.provenance import action as provenance_action
from pf.provenance import read_all

TOOL_METRIC = "aidf.metric"
TOOL_BREAKER = "aidf.breaker"


class BudgetExceeded(RuntimeError):
    """The per-invocation iteration budget is spent."""


@dataclass(frozen=True)
class BreakerState:
    open: bool
    consecutive_failures: int
    limit: int
    reason: str
    last_action_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"open": self.open, "consecutive_failures": self.consecutive_failures,
                "limit": self.limit, "reason": self.reason, "last_action_id": self.last_action_id}


class CircuitBreaker:
    def __init__(self, root: Path, group: str, project: str, budgets: dict[str, Any]) -> None:
        self.root = root
        self.group = group
        self.project = project
        self.limit = int(budgets.get("max_consecutive_validation_failures", 3) or 0)
        self.max_iterations = int(budgets.get("max_iterations_per_invocation", 50) or 0)
        self.enabled = bool(budgets.get("trip_circuit_breaker_on_breach", True))
        self.iterations = 0

    # -- reading the chain ---------------------------------------------------
    def _executions(self) -> list:
        try:
            records = read_all(self.root)
        except (OSError, ValueError):
            return []
        return [r for r in records
                if r.stage == "execution" and r.group == self.group and r.project == self.project
                and r.tool in (TOOL_METRIC, TOOL_BREAKER)]

    def state(self) -> BreakerState:
        fails = 0
        last = ""
        for r in reversed(self._executions()):
            status = str(r.payload.get("aidf_status") or "")
            if r.tool == TOOL_BREAKER:
                if r.payload.get("status") == "ok":
                    break  # a reset marker
                continue
            if status == "PASS":
                break
            if status == "REJECT":
                fails += 1
                last = last or r.action_id
                continue
            # CIRCUIT_BROKEN and ESCALATED: neither counts nor clears.
        opened = self.enabled and self.limit > 0 and fails >= self.limit
        reason = (f"{fails} consecutive validation failures (limit {self.limit}); "
                  f"reset with `pf govern breaker {self.group} {self.project} --reset --reason ...`"
                  if opened else "")
        return BreakerState(opened, fails, self.limit, reason, last)

    def check(self) -> tuple[bool, str]:
        s = self.state()
        return (not s.open), s.reason

    # -- the per-invocation budget ----------------------------------------
    def note_iteration(self) -> None:
        self.iterations += 1
        if self.max_iterations and self.iterations > self.max_iterations:
            raise BudgetExceeded(
                f"{self.iterations} evaluations in one invocation exceeds "
                f"max_iterations_per_invocation={self.max_iterations}")

    # -- resetting -----------------------------------------------------------
    def reset(self, reason: str) -> str:
        """Write the clean marker. Returns the action id, so the reset is citable."""
        if not reason or not reason.strip():
            raise ValueError("a breaker reset needs a reason; it is recorded")
        with provenance_action(self.root, tool=TOOL_BREAKER, target=f"{self.group}/{self.project}",
                               summary=f"circuit breaker reset: {reason.strip()[:200]}",
                               group=self.group, project=self.project) as a:
            a["detail"] = reason.strip()[:400]
            aid = a["action_id"]
        return aid
