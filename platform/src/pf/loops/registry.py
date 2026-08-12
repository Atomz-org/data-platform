"""The loop catalogue.

loop-engineering's reference patterns are software-delivery loops (PR babysitter,
CI sweeper, dependency sweeper). A data platform's loops watch different things:
freshness, schema drift, metric coverage, index staleness. The *shape* is theirs —
cadence, autonomy level, token budget, escalation — the subjects are ours.

Every loop here is L1 (report-only) or L2 (patches inside the gate). Nothing is
L3, because nothing has a track record yet. That ordering is the point.
"""

from __future__ import annotations

import json
from pathlib import Path

from pf.loops.runner import LoopRun, LoopSpec

SPECS: dict[str, LoopSpec] = {
    "freshness-triage": LoopSpec(
        name="freshness-triage",
        description="Read monitor results; report stale sources and volume anomalies.",
        autonomy="L1", cadence="every 2h", token_budget=4_000, writes=False,
    ),
    "test-failure-triage": LoopSpec(
        name="test-failure-triage",
        description="Classify failing dbt nodes from run_results.json into a root cause.",
        autonomy="L1", cadence="on dbt failure", token_budget=12_000, writes=False,
    ),
    "metric-gap-harvester": LoopSpec(
        name="metric-gap-harvester",
        description="Find marts with no metric coverage; propose metric definitions.",
        autonomy="L1", cadence="daily", token_budget=8_000, writes=False,
    ),
    "index-refresher": LoopSpec(
        name="index-refresher",
        description="Rebuild the knowledge graph and context card when manifests move.",
        autonomy="L2", cadence="on manifest change", token_budget=0, writes=True,
    ),
    "impact-sentinel": LoopSpec(
        name="impact-sentinel",
        description="Report the blast radius of every uncommitted model/source change.",
        autonomy="L1", cadence="pre-commit", token_budget=0, writes=False,
    ),
    "pii-audit": LoopSpec(
        name="pii-audit",
        description="Flag PII columns that reach a mart without a masking policy.",
        autonomy="L1", cadence="daily", token_budget=0, writes=False,
    ),
}


# ---------------------------------------------------------------- bodies ----
def freshness_triage(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf import obs

    rows = obs.query(
        "SELECT resource, column_name, monitor, status, message FROM monitor_results "
        "WHERE project = ? AND status <> 'ok' ORDER BY ts DESC LIMIT 20", [project])
    return [f"{r['resource']}.{r['column_name']} [{r['monitor']}] {r['status']}: {r['message']}"
            for r in rows]


def test_failure_triage(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.runtime.dbt_runtime import failed_nodes

    pdir = root / "groups" / group / "projects" / project
    return [f"{n['unique_id']}: {n['status']} — {(n['message'] or '')[:160]}"
            for n in failed_nodes(pdir)]


def metric_gap_harvester(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.kg.store import open_graph

    gp = root / "groups" / group / "projects" / project / "kg" / "graph.duckdb"
    if not gp.exists():
        return []
    with open_graph(gp, read_only=True) as g:
        marts = [m for m in g.nodes("Model") if m.layer == "marts"]
        covered = set()
        for metric in g.nodes("Metric"):
            for e in g.in_edges(metric.id):
                covered.add(e.src)
    gaps = [m for m in marts if m.id not in covered]
    return [f"mart `{m.name}` (grain: {m.props.get('grain', '?')}) has no metric "
            f"measuring it — every question about it falls back to raw SQL"
            for m in gaps]


def index_refresher(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.kg.build import build_graph
    from pf.kg.card import render_project_card

    pdir = root / "groups" / group / "projects" / project
    manifest = pdir / "transform" / "target" / "manifest.json"
    graph = pdir / "kg" / "graph.duckdb"
    if graph.exists() and manifest.exists() and \
       graph.stat().st_mtime >= manifest.stat().st_mtime:
        return []
    counts = build_graph(pdir, group=group, project=project)
    render_project_card(pdir, group, project)
    return [f"rebuilt index: {sum(counts.values())} nodes across {len(counts)} kinds"]


def impact_sentinel(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    import subprocess

    from pf.kg.impact import impact_of_many

    pdir = root / "groups" / group / "projects" / project
    proc = subprocess.run(["git", "status", "--porcelain", "--", str(pdir)],
                          capture_output=True, text=True, cwd=str(root))
    nodes: list[str] = []
    for line in proc.stdout.splitlines():
        p = Path(line[3:].strip().strip('"'))
        if p.suffix == ".sql" and "models" in p.parts:
            nodes.append(f"model:{p.stem}")
    if not nodes:
        return []
    gp = pdir / "kg" / "graph.duckdb"
    if not gp.exists():
        return ["graph not built; cannot assess impact"]
    report = impact_of_many(gp, sorted(set(nodes)))
    if not report.total:
        return []
    owners = ", ".join(report.owners) or "no owner declared"
    return [f"{report.severity.upper()}: {', '.join(sorted(set(nodes)))} affects "
            f"{report.total} object(s); notify {owners}"]


def pii_audit(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.kg.store import open_graph

    gp = root / "groups" / group / "projects" / project / "kg" / "graph.duckdb"
    if not gp.exists():
        return []
    with open_graph(gp, read_only=True) as g:
        marts = {m.id for m in g.nodes("Model") if m.layer == "marts"}
        leaked = []
        for col in g.nodes("Column"):
            if not col.props.get("pii"):
                continue
            for e in g.in_edges(col.id):
                if e.src in marts:
                    leaked.append(f"{col.props.get('model')}.{col.name}")
    return [f"PII column `{c}` reaches a mart — confirm a masking policy or an "
            f"explicit waiver" for c in sorted(set(leaked))]


BODIES = {
    "freshness-triage": freshness_triage,
    "test-failure-triage": test_failure_triage,
    "metric-gap-harvester": metric_gap_harvester,
    "index-refresher": index_refresher,
    "impact-sentinel": impact_sentinel,
    "pii-audit": pii_audit,
}
