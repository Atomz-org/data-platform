"""Loop Readiness Score.

loop-engineering scores a repo 0–100 on whether it is safe to hand a loop more
autonomy. The dimensions are theirs; the checks are adapted to this platform —
a data platform's readiness includes an ontology that validates and a graph that
can compute blast radius, because those are what make an autonomous change safe.

Score >= 80 means L2 is defensible. L3 needs a track record in the ledger too.
"""

from __future__ import annotations

import json
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
    mdl: bool

    @property
    def ready(self) -> bool:
        return self.hook and self.graph and self.card and self.claude_md and self.mdl

    @property
    def missing(self) -> list[str]:
        return [n for n, ok in (("hook", self.hook), ("graph", self.graph),
                                ("card", self.card), ("CLAUDE.md", self.claude_md),
                                ("mdl", self.mdl)) if not ok]


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
                hook=settings.exists() and "PreToolUse" in settings.read_text(encoding="utf-8"),
                graph=(p / "kg" / "graph.duckdb").exists(),
                card=(p / "kg" / "context_card.md").exists(),
                claude_md=(p / "CLAUDE.md").exists(),
                mdl=(p / "mdl" / "mdl.json").exists(),
            ))
    return out


def _marketplace_resolves(root: Path) -> tuple[bool, str]:
    """Does every plugin the marketplace advertises actually exist on disk?

    Checks what `claude plugin validate` checks, without shelling out to a CLI
    that may not be installed wherever the audit runs: sources are relative to
    the marketplace root (the directory holding `.claude-plugin/`), must not
    escape it, and must land on a directory containing a plugin manifest.
    """
    manifest = root / "platform" / ".claude-plugin" / "marketplace.json"
    if not manifest.exists():
        return False, "platform/.claude-plugin/marketplace.json missing — no toolkit loads"
    try:
        entries = (json.loads(manifest.read_text(encoding="utf-8")) or {}).get("plugins") or []
    except json.JSONDecodeError as exc:
        return False, f"marketplace.json does not parse: {exc}"
    if not entries:
        return False, "marketplace lists no plugins"

    market_root = manifest.parent.parent
    broken = []
    for e in entries:
        src = str(e.get("source", ""))
        if src.startswith("..") or "/../" in src:
            broken.append(f"{e.get('name')} (escapes marketplace root)")
            continue
        if not (market_root / src / ".claude-plugin" / "plugin.json").exists():
            broken.append(f"{e.get('name')} (no plugin.json at {src})")
    if broken:
        return False, f"{len(broken)}/{len(entries)} unresolvable: {', '.join(broken[:3])}"
    return True, f"{len(entries)} plugin(s) resolve"


def _mcp_wired(root: Path, projects: list[ProjectReadiness]) -> tuple[bool, str]:
    """Can a project session actually call the graph tools its CLAUDE.md names?"""
    server = root / "platform" / "toolkits" / "power-tools" / ".mcp.json"
    if not server.exists():
        return False, "no toolkit ships .mcp.json — kg_search/impact_analysis unavailable"

    missing = []
    for p in projects:
        settings = root / "groups" / p.group / "projects" / p.project / ".claude" / "settings.json"
        if not settings.exists() or "power-tools@platform" not in settings.read_text(encoding="utf-8"):
            missing.append(f"{p.group}/{p.project}")
    if missing:
        return False, f"not enabled in {len(missing)} project(s): {', '.join(missing[:3])}"
    return True, f"enabled in {len(projects)}/{len(projects)} project(s)"


def audit(root: Path) -> tuple[int, list[Check]]:
    from pf.loops.runner import Ledger

    checks: list[Check] = []

    def add(name: str, weight: int, passed: bool, detail: str) -> None:
        checks.append(Check(name, weight, passed, detail))

    # -- governance --------------------------------------------------------
    gate = root / "gate.yaml"
    policy = yaml.safe_load(gate.read_text(encoding="utf-8")) if gate.exists() else {}
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
    root_hook = settings.exists() and "PreToolUse" in settings.read_text(encoding="utf-8")
    hooked = [p for p in projects if p.hook]
    add("PreToolUse hook wired", 10, root_hook and len(hooked) == n,
        f"root + {len(hooked)}/{n} project(s)" if root_hook
        else "root settings.json has no PreToolUse block")

    # The toolkits are only capabilities if a session can actually load them.
    # They were all individually valid and none of them resolved for months: the
    # marketplace listed each source as `../platform/toolkits/<x>`, which walks
    # out of the repo, and the marketplace projects point at did not exist. That
    # failure is completely silent — plugins simply do not appear — so it needs a
    # check rather than a convention.
    ok_market, market_detail = _marketplace_resolves(root)
    add("plugin marketplace resolves", 10, ok_market, market_detail)

    # `pf mcp` exposes kg_search, kg_neighbors, kg_path and impact_analysis. Every
    # project CLAUDE.md instructs the agent to call them before reading files or
    # changing a column. Without a plugin shipping `.mcp.json`, those tools do not
    # exist in the session and the instruction is a dead letter.
    ok_mcp, mcp_detail = _mcp_wired(root, projects)
    add("MCP tools available to projects", 10, ok_mcp, mcp_detail)

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
