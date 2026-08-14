"""The live tier: call the real models and grade what comes back.

Two things make this different from running the loops by hand.

**Sampling.** These calls are not deterministic, and a suite that samples each
case once reports flakiness as a failure on whichever run happened to lose. A
case that passes 4 times in 5 is not a passing case and it is not a failing one
either — it is an unstable prompt, and that is the single most useful thing an
eval suite can tell you before you ship a prompt change. So `samples` is a knob,
the pass rate is always reported, and the default is strict: every sample must
pass.

**Spend is reported, not hidden.** Live evals cost real money on every run. The
token count comes from the same counter the loop runner uses to enforce its
budget, so an eval suite is billed and measured exactly like the loop it stands
in for.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from pf.agents import loops as loop_agents
from pf.agents.base import NoCredentials, have_credentials, reset_spend, spend
from pf.evals.case import Case
from pf.evals.grade import GradeFailure, grade

# The callable each agent name drives. The loop body and the eval call the same
# function — an eval that reimplemented the prompt would be testing itself.
DISPATCH = {
    "test_failure_triage": loop_agents.triage_failures,
    "freshness_triage": loop_agents.assess_anomaly,
    "metric_gap_proposer": loop_agents.propose_metrics,
}


@dataclass
class CaseResult:
    case: Case
    samples: int = 0
    passed: int = 0
    failures: list[GradeFailure] = field(default_factory=list)
    error: str = ""
    tokens: int = 0
    duration_ms: int = 0

    @property
    def ok(self) -> bool:
        return not self.error and self.samples > 0 and self.passed == self.samples

    @property
    def flaky(self) -> bool:
        """Passed sometimes. Distinct from failing — the prompt is unstable, not
        wrong, and the fix is usually different."""
        return not self.error and 0 < self.passed < self.samples

    @property
    def pass_rate(self) -> str:
        return f"{self.passed}/{self.samples}"


@dataclass
class Report:
    results: list[CaseResult] = field(default_factory=list)
    tokens: int = 0
    usd: float = 0.0

    @property
    def failed(self) -> list[CaseResult]:
        return [r for r in self.results if not r.ok]

    @property
    def flaky(self) -> list[CaseResult]:
        return [r for r in self.results if r.flaky]

    @property
    def ok(self) -> bool:
        return not self.failed


def run_live(root: Path, group: str, project: str, cases: list[Case],
             samples: int = 1) -> Report:
    """Run every case against the real models and grade the responses."""
    if not have_credentials():
        raise NoCredentials(
            "live evals need a credential (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN "
            "or an `ant auth login` profile). The contract tier runs without one.")

    report = Report()
    started = time.time()
    reset_spend()

    for case in cases:
        report.results.append(_run_case(root, group, project, case, samples))

    report.tokens = spend()
    report.usd = _spend_usd(root, started)
    return report


def _run_case(root: Path, group: str, project: str, case: Case,
              samples: int) -> CaseResult:
    result = CaseResult(case=case)
    fn = DISPATCH[case.agent]
    before, t0 = spend(), time.time()

    for _ in range(samples):
        try:
            parsed = fn(root, group, project, **case.input)
        except Exception as exc:  # noqa: BLE001 — one bad case must not end the suite
            result.error = f"{type(exc).__name__}: {exc}"
            break

        result.samples += 1
        failures = grade(parsed, case.expect)
        if failures:
            # Keep the first failing sample's reasons. Later samples that fail
            # differently are noise in the report; the pass rate already says
            # the case is unstable.
            if not result.failures:
                result.failures = failures
        else:
            result.passed += 1

    result.tokens = spend() - before
    result.duration_ms = int((time.time() - t0) * 1000)
    return result


def _spend_usd(root: Path, since: float) -> float:
    """Cost of this suite, from the same ledger every agent run is recorded in.

    Best-effort: a missing or locked observability database must not fail an
    otherwise complete eval run.
    """
    from datetime import UTC, datetime

    try:
        from pf import obs

        rows = obs.query(
            "SELECT COALESCE(SUM(cost_usd), 0) AS usd FROM agent_runs WHERE ts >= ?",
            [datetime.fromtimestamp(since, tz=UTC)],
            root=root,
        )
        return round(float(rows[0]["usd"]), 4) if rows else 0.0
    except Exception:  # noqa: BLE001
        return 0.0
