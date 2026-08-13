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
    "dashboard-coverage": LoopSpec(
        name="dashboard-coverage",
        description="Score the reporting layer; find metrics no page shows and pages "
                    "referencing metrics that do not exist.",
        autonomy="L1", cadence="daily", token_budget=0, writes=False,
    ),
    "pii-audit": LoopSpec(
        name="pii-audit",
        description="Flag PII columns that reach a mart without a masking policy.",
        autonomy="L1", cadence="daily", token_budget=0, writes=False,
    ),
    "vendor-drift": LoopSpec(
        name="vendor-drift",
        description="Report vendored upstreams that moved, and which of our files "
                    "each movement implicates.",
        autonomy="L1", cadence="weekly", token_budget=0, writes=False,
    ),
}


# ---------------------------------------------------------------- bodies ----
def freshness_triage(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf import obs
    from pf.agents import NoCredentials, assess_anomaly, have_credentials

    rows = obs.query(
        "SELECT resource, column_name, monitor, status, observed, expected, "
        "deviation_pct, message FROM monitor_results "
        "WHERE project = ? AND status <> 'ok' ORDER BY ts DESC LIMIT 20", [project])
    raw = [f"{r['resource']}.{r['column_name']} [{r['monitor']}] {r['status']}: {r['message']}"
           for r in rows]
    if not raw or not have_credentials():
        return raw  # deterministic findings are the fallback, not an error

    try:
        report = assess_anomaly(root, group, project, rows)
    except NoCredentials:
        return raw
    if report is None:
        return raw
    if report.ignorable:
        return []  # judged noise; do not put it in STATE.md
    return [f"[{report.severity}] {report.headline} — likely: {report.likely_cause}"]


def test_failure_triage(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.agents import NoCredentials, have_credentials, triage_failures
    from pf.kg.query import kg_neighbors
    from pf.runtime.dbt_runtime import failed_nodes

    pdir = root / "groups" / group / "projects" / project
    failures = failed_nodes(pdir)
    raw = [f"{n['unique_id']}: {n['status']} — {(n['message'] or '')[:160]}"
           for n in failures]
    if not failures or not have_credentials():
        return raw

    # Lineage from the graph, not from grep: this is what keeps the prompt small.
    gp = pdir / "kg" / "graph.duckdb"
    lineage = ""
    if gp.exists():
        for f in failures[:3]:
            model = (f["unique_id"] or "").split(".")[-1]
            lineage += kg_neighbors(gp, f"model:{model}", depth=1) + "\n\n"

    try:
        d = triage_failures(root, group, project, failures, lineage)
    except NoCredentials:
        return raw
    if d is None:
        return raw
    prefix = "ESCALATE" if d.escalate else d.confidence.upper()
    return [f"[{prefix}] root_cause={d.root_cause}: {d.summary} → {d.suggested_fix}"]


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
    raw = [f"mart `{m.name}` (grain: {m.props.get('grain', '?')}) has no metric "
           f"measuring it — every question about it falls back to raw SQL"
           for m in gaps]

    from pf.agents import NoCredentials, have_credentials, propose_metrics
    if not gaps or not have_credentials():
        return raw

    with open_graph(gp, read_only=True) as g:
        detail = ""
        for m in gaps:
            cols = [g.node(e.dst) for e in g.out_edges(m.id)]
            names = [f"{c.name}({c.props.get('role') or c.props.get('data_type') or '?'})"
                     for c in cols if c and c.kind == "Column"]
            detail += f"{m.name} [grain: {m.props.get('grain','?')}]: {', '.join(names)}\n"

    try:
        proposals = propose_metrics(root, group, project,
                                    [m.name for m in gaps], detail)
    except NoCredentials:
        return raw
    if proposals is None or not proposals.proposals:
        return raw
    return [f"propose metric `{p.metric_name}` ({p.metric_type}) on {p.measure_or_expr}"
            f"{' where ' + p.filter_expression if p.filter_expression else ''} — {p.rationale}"
            for p in proposals.proposals]


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


def dashboard_coverage(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.projections.report_audit import audit as audit_report

    pdir = root / "groups" / group / "projects" / project
    if not (pdir / "reporting").exists():
        return []
    score, findings = audit_report(pdir)
    out = [str(f) for f in findings if f.severity in ("error", "warning")]
    if score < 90:
        out.insert(0, f"report score {score}/100 — run the dashboard-loop skill")
    return out


def vendor_drift(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    """Upstream movement, translated into files a person should re-read.

    L1 and staying there. Bumping a submodule is a one-line commit an agent could
    trivially make, and that is exactly why it must not: the value of the pin is
    that someone read the diff, and an automatic bump destroys the only evidence
    that anyone did.

    Repo-scoped rather than project-scoped — the vendored upstreams are shared —
    so it reports once and not once per sister company.
    """
    from pf.vendor.model import drift

    out: list[str] = []
    for d in drift(root):
        if not d.current:
            out.append(f"{d.upstream_id}: submodule not checked out")
            continue
        if not d.locked:
            out.append(f"{d.upstream_id}: never reviewed — `pf vendor approve {d.upstream_id}`")
            continue
        if not d.needs_review:
            continue
        behind = f"{d.commits_behind} commit(s)" if d.commits_behind >= 0 else "shallow"
        files = ", ".join(d.affected_files()[:4]) or "no derived file recorded"
        out.append(f"[{d.severity}] {d.upstream_id} moved {behind}; "
                   f"{len(d.paths)} adopted path(s) changed — re-read {files}")
    return out


BODIES = {
    "dashboard-coverage": dashboard_coverage,
    "vendor-drift": vendor_drift,
    "freshness-triage": freshness_triage,
    "test-failure-triage": test_failure_triage,
    "metric-gap-harvester": metric_gap_harvester,
    "index-refresher": index_refresher,
    "impact-sentinel": impact_sentinel,
    "pii-audit": pii_audit,
}
