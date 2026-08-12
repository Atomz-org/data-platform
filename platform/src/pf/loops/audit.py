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


@dataclass(frozen=True)
class ProjectReadiness:
    """Per-project governance state.

    The repo-level score used to ask "does *any* project have a graph", which a
    newly scaffolded project could hide behind indefinitely: the aggregate stayed
    green while the new project had no graph, no card and — before the template
    was fixed — no PreToolUse hook at all. Readiness is per project or it is not
    readiness.
    """

    group: str
    project: str
    hook: bool
    graph: bool
    card: bool
    claude_md: bool

    @property
    def ready(self) -> bool:
        return self.hook and self.graph and self.card and self.claude_md

    @property
    def missing(self) -> list[str]:
        return [n for n, ok in (("hook", self.hook), ("graph", self.graph),
                                ("card", self.card), ("CLAUDE.md", self.claude_md)) if not ok]


def project_readiness(root: Path) -> list[ProjectReadiness]:
    """Governance state for every project, newest scaffold included."""
    out: list[ProjectReadiness] = []
    gdir = root / "groups"
    if not gdir.exists():
        return out
    for g in sorted(x for x in gdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
        pdir = g / "projects"
        if not pdir.exists():
            continue
        for p in sorted(x for x in pdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
            settings = p / ".claude" / "settings.json"
            out.append(ProjectReadiness(
                group=g.name,
                project=p.name,
                hook=settings.exists() and "PreToolUse" in settings.read_text(),
                graph=(p / "kg" / "graph.duckdb").exists(),
                card=(p / "kg" / "context_card.md").exists(),
                claude_md=(p / "CLAUDE.md").exists(),
            ))
    return out


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

    # Every check below is "all projects", not "any project" — a new project
    # must drag the score down until it is governed, or scaffolding one is a
    # silent hole.
    projects = project_readiness(root)
    n = len(projects)

    settings = root / ".claude" / "settings.json"
    root_hook = settings.exists() and "PreToolUse" in settings.read_text()
    hooked = [p for p in projects if p.hook]
    add("PreToolUse hook wired", 10, root_hook and len(hooked) == n,
        f"root + {len(hooked)}/{n} project(s)" if root_hook
        else "root settings.json has no PreToolUse block")

    # -- platform-specific readiness ---------------------------------------
    graphed = [p for p in projects if p.graph]
    add("knowledge graph built", 10, n > 0 and len(graphed) == n,
        f"{len(graphed)}/{n} project(s)"
        + ("" if len(graphed) == n else
           f" — ungoverned: {', '.join(f'{p.group}/{p.project}' for p in projects if not p.graph)}"))

    carded = [p for p in projects if p.card]
    add("context cards generated", 5, n > 0 and len(carded) == n, f"{len(carded)}/{n} card(s)")

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
