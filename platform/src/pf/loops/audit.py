"""Loop Readiness Score.

loop-engineering scores a repo 0–100 on whether it is safe to hand a loop more
autonomy. The dimensions are theirs; the checks are adapted to this platform —
a data platform's readiness includes an ontology that validates and a graph that
can compute blast radius, because those are what make an autonomous change safe.

Score >= 80 means L2 is defensible. L3 needs a track record in the ledger too.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Check:
    name: str
    weight: int
    passed: bool
    detail: str


def audit(root: Path) -> tuple[int, list[Check]]:
    from pf.loops.runner import Ledger

    checks: list[Check] = []

    def add(name: str, weight: int, passed: bool, detail: str) -> None:
        checks.append(Check(name, weight, passed, detail))

    # -- governance --------------------------------------------------------
    gate = root / "gate.yaml"
    policy = yaml.safe_load(gate.read_text()) if gate.exists() else {}
    add("gate.yaml present", 10, gate.exists(), str(gate.relative_to(root)) if gate.exists() else "missing")
    add("denylist populated", 10, len(policy.get("denylist") or []) >= 5,
        f"{len(policy.get('denylist') or [])} patterns")
    add("maxFiles set", 5, bool(policy.get("maxFiles")), str(policy.get("maxFiles", "unset")))

    for f, w in (("LOOP.md", 10), ("STATE.md", 10), ("loop-constraints.md", 10)):
        add(f"{f} present", w, (root / f).exists(), "" if (root / f).exists() else "missing")

    # -- enforcement (the part that is usually missing) --------------------
    hook = root / ".git" / "hooks" / "pre-commit"
    add("pre-commit gate installed", 10, hook.exists(), "" if hook.exists() else "not linked")

    settings = root / ".claude" / "settings.json"
    has_pretool = settings.exists() and "PreToolUse" in settings.read_text()
    add("PreToolUse hook wired", 10, has_pretool,
        "" if has_pretool else "an agent can edit a model with no blast radius shown")

    # -- platform-specific readiness ---------------------------------------
    graphs = list(root.glob("groups/*/projects/*/kg/graph.duckdb"))
    add("knowledge graph built", 10, bool(graphs), f"{len(graphs)} project(s)")

    cards = list(root.glob("groups/*/projects/*/kg/context_card.md"))
    add("context cards generated", 5, bool(cards), f"{len(cards)} card(s)")

    ledger = Ledger(root)
    entries = ledger.read()
    add("ledger has runs", 5, bool(entries), f"{len(entries)} run(s)")

    # -- autonomy track record --------------------------------------------
    clean = [e for e in entries if e.get("outcome") in ("ok", "noop")]
    ratio = len(clean) / len(entries) if entries else 0
    add("run success ratio >= 0.8", 5, ratio >= 0.8 and bool(entries),
        f"{ratio:.0%}" if entries else "no history")

    total = sum(c.weight for c in checks)
    earned = sum(c.weight for c in checks if c.passed)
    return round(100 * earned / total), checks


def recommended_level(score: int, root: Path) -> str:
    from pf.loops.runner import Ledger

    runs = len(Ledger(root).read())
    if score >= 80 and runs >= 50:
        return "L3 defensible — but only for loops with their own track record"
    if score >= 80:
        return f"L2 (assisted fixes). L3 needs a track record; ledger has {runs} run(s)"
    if score >= 55:
        return "L1 (report-only) until the failing checks are closed"
    return "L1 only — governance is incomplete"
