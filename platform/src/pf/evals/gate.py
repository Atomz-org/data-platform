"""Evals as a gate — on every change that alters what the agent is.

`pf check` gates SQL on conformance and blast radius. Nothing gated the other
half of the platform: a prompt edit, a model bump, a skill rewrite, a vendor pin
moving under a toolkit. Each of those changes the agent's behaviour, and each
shipped green because no test knew to run. This module is the missing symmetry.

Two questions, both answered from the diff:

  1. **Does this change touch the agent surface?** A small, explicit list of
     globs — the routing table, the prompts, the skills, the loop registry, the
     MCP server, the pins. Touching any of them makes the eval tier mandatory.
  2. **Do the evals pass?** Contract always (free, deterministic). Live when
     asked, or when the change is to a prompt or routing — the two kinds of
     edit the contract tier cannot see.

Whatever ran is written to `data/evals/latest.json`. That file is what
`pf.loops.levels` reads when deciding whether a loop may climb: promotion and
merge consume the same scores, so a loop cannot be promoted on evidence that a
merge would have refused.

## Why the surface is a list and not "anything under platform/"

A gate that fires on every platform change is one people learn to skip. The
list is what an engineer would name if asked "what changes the agent" — and the
test pins it, so adding a prompt somewhere new without adding it here fails a
test rather than silently evading the gate.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Paths whose change alters the agent. Glob, repo-relative, forward slashes.
AGENT_SURFACE: tuple[str, ...] = (
    "platform/src/pf/agents/**",          # prompts, routing, schemas
    "platform/src/pf/loops/registry.py",  # what loops do with a verdict
    "platform/src/pf/loops/actions.py",   # what a proposal may become
    "platform/src/pf/mcp/**",             # the tools an agent session sees
    "platform/toolkits/**/SKILL.md",      # how an agent is told to work
    "platform/toolkits/**/skills/**",
    "platform/toolkits/**/agents/**",
    "platform/toolkits/ROUTING.md",
    "platform/toolkits/**/evals/**",      # the evals themselves
    "loop-constraints.md",
    "loop-budget.md",
    ".gitmodules",                        # a vendor pin moved
)

#: The subset whose change the contract tier cannot see — only live grading can.
LIVE_REQUIRED: tuple[str, ...] = (
    "platform/src/pf/agents/loops.py",
    "platform/src/pf/agents/ask.py",
    "platform/src/pf/agents/base.py",
    "platform/toolkits/**/SKILL.md",
    "platform/toolkits/**/skills/**",
)


def _norm(p: str) -> str:
    return p.replace("\\", "/").removeprefix("./")


def _hits(paths: list[str], patterns: tuple[str, ...]) -> list[str]:
    out = []
    for p in paths:
        n = _norm(p)
        for pat in patterns:
            if fnmatch.fnmatch(n, pat) or fnmatch.fnmatch(n, pat.replace("**/", "")):
                out.append(n)
                break
    return out


def touches_agent_surface(changed: list[str]) -> list[str]:
    return _hits(changed, AGENT_SURFACE)


def needs_live(changed: list[str]) -> list[str]:
    return _hits(changed, LIVE_REQUIRED)


# ---------------------------------------------------------------- report ----
@dataclass
class GateReport:
    changed: list[str] = field(default_factory=list)
    surface: list[str] = field(default_factory=list)
    live_required: list[str] = field(default_factory=list)
    contract_ok: bool | None = None
    contract: list[dict[str, str]] = field(default_factory=list)
    live_ran: bool = False
    live_ok: bool | None = None
    live_pass_rate: float | None = None
    live_cases: int = 0
    live_tokens: int = 0
    skipped_reason: str = ""
    message: str = ""

    @property
    def required(self) -> bool:
        return bool(self.surface)

    @property
    def ok(self) -> bool:
        if not self.required:
            return True
        if self.contract_ok is False:
            return False
        if self.live_required and not self.live_ran:
            return False
        return not (self.live_ran and not self.live_ok)

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__} | {
            "required": self.required, "ok": self.ok}


def latest_path(root: Path) -> Path:
    return root / "data" / "evals" / "latest.json"


def record(root: Path, *, contract: dict[str, Any] | None = None,
           live: dict[str, Any] | None = None) -> Path:
    """Merge a tier's result into latest.json; other tiers keep their last value."""
    p = latest_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {}
    if p.exists():
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            doc = {}
    now = datetime.now(UTC).isoformat(timespec="seconds")
    if contract is not None:
        doc["contract"] = contract | {"at": now}
    if live is not None:
        doc["live"] = live | {"at": now}
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return p


def run_gate(root: Path, group: str, project: str, *, changed: list[str],
             live: bool = False, samples: int = 1, force: bool = False) -> GateReport:
    """Decide whether evals are required for this diff, run them, record them."""
    from pf.evals import discover, run_contract

    rep = GateReport(changed=[_norm(c) for c in changed])
    rep.surface = touches_agent_surface(rep.changed)
    rep.live_required = needs_live(rep.changed)
    if not rep.surface and not force:
        rep.skipped_reason = "no agent-surface file changed"
        return rep

    results = run_contract(root, group, project)
    rep.contract = [{"name": r.name, "outcome": r.outcome, "detail": r.detail} for r in results]
    rep.contract_ok = all(r.outcome != "fail" for r in results)
    record(root, contract={"ok": rep.contract_ok,
                           "checks": len(results),
                           "failed": [r.name for r in results if r.outcome == "fail"]})

    if not live:
        if rep.live_required:
            rep.message = (f"{len(rep.live_required)} prompt/skill file(s) changed — "
                           f"live evals required: `pf evals-gate {group} {project} --live`")
        return rep

    from pf.agents.base import NoCredentials, have_credentials
    from pf.evals import run_live

    if not group or not project:
        rep.message = "live evals need a group and a project"
        return rep
    if not have_credentials():
        rep.message = "live evals need a credential"
        return rep
    cases = discover(root, group, project)
    try:
        report = run_live(root, group, project, cases, samples=samples)
    except NoCredentials as exc:
        rep.message = str(exc)
        return rep
    total = sum(r.samples for r in report.results)
    passed = sum(r.passed for r in report.results)
    rep.live_ran = True
    rep.live_ok = report.ok
    rep.live_cases = len(report.results)
    rep.live_tokens = report.tokens
    rep.live_pass_rate = round(passed / total, 3) if total else 0.0
    record(root, live={"ok": rep.live_ok, "pass_rate": rep.live_pass_rate,
                       "cases": rep.live_cases, "tokens": rep.live_tokens,
                       "group": group, "project": project,
                       "failed": [r.case.qualified_name for r in report.failed]})
    return rep
