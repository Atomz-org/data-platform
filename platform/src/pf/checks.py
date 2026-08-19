"""The three-state check — one condition, its verdict, and the evidence for it.

Lifted out of `pf.onboard.ladder`, which defined it first and still re-exports it.
The move happened when `pf.air` needed the same vocabulary to report control
coverage: importing it from `ladder` would have dragged `dialect`, `survey` and
`audit` into every `pf air` invocation to reuse a 12-line dataclass, and defining
a second one would have made three (`pf.loops.audit.Check` is a different thing —
a weighted pass/fail for a readiness *score*, not a gate condition).

## Why three states and not two

`unexercised` is not a polite failure. It is the honest answer when the thing
that would decide is absent — the tool is not installed, the ledger has no
records yet, the submodule is not checked out — and it is reported loudly rather
than counted as either. Collapsing it into `fail` walls a project off over a
missing binary; collapsing it into `pass` is how a control that has never run
reads as a control that works.

**Only `fail` closes a gate.** That rule lives in `ok` and every caller inherits
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["pass", "fail", "unexercised"]

__all__ = ["Check", "Status", "failed", "passed", "unexercised"]


@dataclass(frozen=True)
class Check:
    """One gate condition, with the evidence for its verdict.

    `evidence` is not a restatement of `name`. A check that says only "failed"
    forces whoever reads it to reproduce the check by hand, which is how a gate
    stops being read at all.
    """

    name: str
    status: Status
    evidence: str

    @property
    def ok(self) -> bool:
        return self.status != "fail"


def passed(name: str, evidence: str) -> Check:
    return Check(name, "pass", evidence)


def failed(name: str, evidence: str) -> Check:
    return Check(name, "fail", evidence)


def unexercised(name: str, evidence: str) -> Check:
    return Check(name, "unexercised", evidence)
