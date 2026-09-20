"""The loop catalogue.

loop-engineering's reference patterns are software-delivery loops (PR babysitter,
CI sweeper, dependency sweeper). A data platform's loops watch different things:
freshness, schema drift, metric coverage, index staleness. The *shape* is theirs —
cadence, autonomy level, token budget, escalation — the subjects are ours.

Every loop here is *born* L1 (report-only) or L2 (patches inside the gate). The
level a loop runs at is the one it has *earned* — `pf.loops.levels` reads the
ledger — and nothing has earned L3 yet. That ordering is the point.

Tools contribute loops too (`Tool.loops`); `all_loops()` is the merged view every
consumer should read. `SPECS`/`BODIES` are the registry's own.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    "vendor-drift": LoopSpec(
        name="vendor-drift",
        description="Report vendored upstreams that moved, and which of our files "
                    "each movement implicates.",
        autonomy="L1", cadence="weekly", token_budget=0, writes=False,
    ),
    "observability-triage": LoopSpec(
        name="observability-triage",
        description="Read Elementary's recorded test history; report what is "
                    "failing or anomalous, with how often — recurrence is the "
                    "difference between an incident and a broken test.",
        autonomy="L1", cadence="every 6h", token_budget=12_000, writes=False,
    ),
    "expectations-refresher": LoopSpec(
        name="expectations-refresher",
        description="Regenerate the ontology-derived expectations floor when the "
                    "knowledge graph has moved past it.",
        autonomy="L2", cadence="on graph change", token_budget=0, writes=True,
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
    except NoCredentials as exc:
        run.message = str(exc)[:400]  # why the model was not asked, in the ledger
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
    except NoCredentials as exc:
        run.message = str(exc)[:400]
        return raw
    if d is None:
        return raw
    prefix = "ESCALATE" if d.escalate else d.confidence.upper()
    finding = f"[{prefix}] root_cause={d.root_cause}: {d.summary} → {d.suggested_fix}"

    # Closing the loop. Only when the diagnosis is one a file in this repo can
    # fix, the model is sure, and nobody said a human must decide first. The
    # proposal is queued on the run; the runner executes it at the level the
    # loop has *earned* — recorded at L1, a reviewed PR at L2, never a merge.
    if (d.escalate or d.confidence != "high"
            or d.root_cause not in ("model_logic", "test_too_strict")):
        return [finding]
    target = _fix_target(pdir, failures[0], d.root_cause)
    if target is None:
        return [finding + " (no file to patch: not in manifest)"]
    rel, current = target
    from pf.agents import draft_fix
    from pf.loops.actions import Proposal
    try:
        patch = draft_fix(root, group, project, diagnosis=d, rel_path=rel,
                          current=current, lineage=lineage)
    except NoCredentials:
        return [finding]
    if patch is None or not patch.safe or patch.path != rel:
        why = "drafter declined" if patch is None or not patch.safe else "path mismatch"
        return [finding + f" (no proposal: {why})"]
    if patch.content == current:
        return [finding + " (no proposal: drafter returned the file unchanged)"]
    run.propose(Proposal(loop="test-failure-triage", title=patch.title,
                         rationale=patch.rationale, files={rel: patch.content},
                         finding=finding, confidence=d.confidence,
                         labels=("loop", "test-failure-triage", d.root_cause)))
    return [finding + f" → proposed: {patch.title}"]


def _fix_target(pdir: Path, failure: dict, root_cause: str) -> tuple[str, str] | None:
    """The one file a diagnosis points at, and its current contents.

    `test_too_strict` edits the file the test is declared in. `model_logic`
    edits the model the test is attached to. Resolved from the manifest rather
    than guessed from a name, so a renamed model is a miss rather than a patch
    to the wrong file.
    """
    import json as _json

    manifest = pdir / "transform" / "target" / "manifest.json"
    if not manifest.exists():
        return None
    nodes = (_json.loads(manifest.read_text(encoding="utf-8")) or {}).get("nodes") or {}
    node = nodes.get(failure.get("unique_id") or "")
    if not node:
        return None
    if root_cause == "model_logic" and node.get("resource_type") == "test":
        attached = node.get("attached_node") or next(
            (n for n in (node.get("depends_on") or {}).get("nodes", [])
             if n.startswith("model.")), "")
        node = nodes.get(attached) or {}
        if not node:
            return None
    ofp = node.get("original_file_path")
    if not ofp:
        return None
    rel = str(Path("transform") / ofp).replace("\\", "/")
    f = pdir / rel
    if not f.exists():
        return None
    return rel, f.read_text(encoding="utf-8")


def metric_gap_harvester(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.kg.store import open_graph
    from pf.loops.config import waived, waivers

    gp = root / "groups" / group / "projects" / project / "kg" / "graph.duckdb"
    if not gp.exists():
        return []
    with open_graph(gp, read_only=True) as g:
        marts = [m for m in g.nodes("Model") if m.layer == "marts"]
        covered = set()
        for metric in g.nodes("Metric"):
            for e in g.in_edges(metric.id):
                covered.add(e.src)
    # A waived mart (a report table with nothing to measure, say) is the group's
    # stated decision, matched on the mart's name so the yaml reads like dbt.
    skip = waivers(root, group, "metric-gap-harvester")
    gaps = [m for m in marts if m.id not in covered and waived(m.name, skip) is None]
    # A finding per mart is right at ten gaps and unreadable at a thousand —
    # jaffle-shop's imported marts produced 993 lines and buried every other
    # loop's findings. Past a screenful, the report aggregates: the count is
    # the finding, the names are a sample, and the full list stays queryable
    # in the graph rather than pasted into STATE.md.
    if len(gaps) > 15:
        sample = ", ".join(m.name for m in gaps[:8])
        raw = [(f"{len(gaps)} of {len(marts)} marts have no metric coverage "
                f"(e.g. {sample}, …) — start with the marts a dashboard reads; "
                f"`kg_search` lists the rest")]
        return raw
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
    except NoCredentials as exc:
        # The proposer enriches `raw`; it is not the finding. A refused key is
        # the one failure that must not throw the gap list away: it did, and
        # three runs later the breaker latched on a loop whose subject was
        # fine. Anything else the proposer raises is a bug and still trips it.
        run.message = str(exc)[:400]
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
    return [(f"{report.severity.upper()}: {', '.join(sorted(set(nodes)))} affects "
            f"{report.total} object(s); notify {owners}")]


def pii_audit(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    from pf.kg.store import open_graph
    from pf.loops.config import waived, waivers

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
    # The "explicit waiver" the finding asks for is a `model.column` entry in
    # the group's loops.yaml, with its reason; matched here so it stops asking.
    skip = waivers(root, group, "pii-audit")
    findings = [f"PII column `{c}` reaches a mart — confirm a masking policy or an "
                f"explicit waiver" for c in sorted(set(leaked)) if waived(c, skip) is None]

    # A label with no policy behind it. The graph knows which columns are PII;
    # until the group manifest existed, nothing recorded how long this family is
    # allowed to keep them or how fast it has to delete them on request. Holding
    # personal data to no stated deadline is the finding, and it is the group's
    # rather than any one sister's, so it is reported once per project only
    # because that is the scope this loop runs at.
    if leaked:
        from pf import groups as groups_mod

        try:
            manifest = groups_mod.load(root, group)
        except groups_mod.GroupError:
            manifest = None
        if manifest is None:
            findings.append(
                f"{len(set(leaked))} PII column(s) in a group with no group.yaml: "
                "no retention period and no erasure deadline are recorded anywhere")
        else:
            missing = [name for name, value in
                       (("data.retention_days", manifest.data.retention_days),
                        ("data.erasure_sla_days", manifest.data.erasure_sla_days))
                       if value is None]
            if missing:
                findings.append(
                    f"{len(set(leaked))} PII column(s) reach a mart but "
                    f"{' and '.join(missing)} is unset in groups/{group}/group.yaml — "
                    "personal data with no stated deadline")
    return findings


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


def watch_list() -> list[str]:
    """The loops above L1, for STATE.md's watch list.

    Read from the registry, not from a group's resolved catalogue: the watch
    list is one slot for the whole platform, and a group that switches
    `index-refresher` off would otherwise blank it for every other group until
    someone else's run wrote it back.
    """
    return [s.name for s in SPECS.values() if s.autonomy != "L1"]


def observability_triage(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    """What Elementary's history says is wrong, weighted by recurrence.

    Reads `main_elementary.elementary_test_results` — every framework's tests
    land there (dbt's own, dbt-expectations, the generated floor, anomaly
    monitors) — rather than the one run_results.json that happened to survive.
    The deterministic findings are the fallback; with credentials the existing
    triage agent classifies them, exactly as `test-failure-triage` does for a
    single run.
    """
    import duckdb

    from pf.runtime.warehouse import Warehouse

    pdir = root / "groups" / group / "projects" / project
    wh = Warehouse.for_project(pdir, group, project)
    if not Path(wh.path).exists():
        return []
    try:
        con = duckdb.connect(str(wh.path), read_only=True)
    except duckdb.Error:
        return []  # a sister holds the write lock — report nothing, not an error
    try:
        if not con.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = "
                "'main_elementary' AND table_name = 'elementary_test_results' "
                "LIMIT 1").fetchone():
            return [f"elementary tables missing — `pf tool elementary run {group} {project}`"]
        rows = con.execute("""
            WITH latest AS (
                SELECT test_unique_id, table_name, column_name, test_name,
                       status, test_results_description, detected_at,
                       row_number() OVER (PARTITION BY test_unique_id
                                          ORDER BY detected_at DESC) AS rn
                FROM main_elementary.elementary_test_results
            ), history AS (
                SELECT test_unique_id,
                       count(*) FILTER (WHERE status <> 'pass') AS bad_runs,
                       count(*) AS runs
                FROM main_elementary.elementary_test_results GROUP BY 1
            )
            SELECT l.table_name, l.column_name, l.test_name, l.status,
                   l.test_results_description, h.bad_runs, h.runs
            FROM latest l JOIN history h USING (test_unique_id)
            WHERE l.rn = 1 AND l.status <> 'pass'
            ORDER BY h.bad_runs DESC LIMIT 20""").fetchall()
    except duckdb.Error as exc:
        return [f"could not read elementary history: {exc}"[:200]]
    finally:
        con.close()

    raw = [f"{t or '?'}{'.' + c if c else ''} [{n}] {s} "
           f"({bad}/{total} runs bad): {(d or '')[:120]}"
           for t, c, n, s, d, bad, total in rows]
    if not raw:
        return []

    from pf.agents import NoCredentials, have_credentials, triage_failures
    if not have_credentials():
        return raw
    failures = [{"unique_id": f"{t or '?'}.{n}", "status": s,
                 "message": f"{bad}/{total} runs bad — {(d or '')[:160]}"}
                for t, c, n, s, d, bad, total in rows]
    try:
        verdict = triage_failures(root, group, project, failures, "")
    except NoCredentials:
        return raw
    if verdict is None:
        return raw
    prefix = "ESCALATE" if verdict.escalate else verdict.confidence.upper()
    return [(f"[{prefix}] root_cause={verdict.root_cause}: {verdict.summary} "
            f"→ {verdict.suggested_fix}")]


def expectations_refresher(root: Path, group: str, project: str, run: LoopRun) -> list[str]:
    """Keep the generated quality floor caught up with the graph.

    The mirror of `index-refresher`, one derivation later: the graph is rebuilt
    from the manifest, and the expectations floor is derived from the graph, so
    a graph newer than the newest generated test means annotations moved and
    the floor may be stale. `write_tests` is already idempotent and
    marker-scoped, so re-deriving over an up-to-date floor writes nothing.
    """
    from pf.tools import expectations as ex

    pdir = root / "groups" / group / "projects" / project
    graph = pdir / "kg" / "graph.duckdb"
    if not graph.exists():
        return []
    tdir = ex.tests_dir(pdir)
    newest = max((f.stat().st_mtime for f in tdir.glob("*.sql")), default=0.0) \
        if tdir.exists() else 0.0
    if newest >= graph.stat().st_mtime:
        return []
    written, unchanged, removed = ex.write_tests(pdir)
    if not (written or removed):
        return []
    return [(f"expectations floor refreshed: {written} written, {removed} stale "
            f"removed ({unchanged} unchanged) — runs on the next `pf seed`")]


BODIES = {
    "vendor-drift": vendor_drift,
    "observability-triage": observability_triage,
    "expectations-refresher": expectations_refresher,
    "freshness-triage": freshness_triage,
    "test-failure-triage": test_failure_triage,
    "metric-gap-harvester": metric_gap_harvester,
    "index-refresher": index_refresher,
    "impact-sentinel": impact_sentinel,
    "pii-audit": pii_audit,
}


# ------------------------------------------------------------ the seam ----
def all_loops() -> dict[str, tuple[LoopSpec, Any]]:
    """Registry loops plus every installed tool's. One place to ask.

    A tool's loop is listed, run, budgeted and promoted exactly like one
    declared here; the only difference is who owns it. A registry name wins a
    collision, and the collision is reported by `pf loop audit` rather than
    silently shadowed.
    """
    out: dict[str, tuple[LoopSpec, Any]] = {n: (SPECS[n], BODIES[n]) for n in SPECS}
    try:
        from pf.tools import all_tools
        tools = all_tools()
    except Exception:  # noqa: BLE001 — a broken plugin must not hide the registry
        return out
    for tool in tools.values():
        if not tool.loops or (tool.missing() and not tool.offline):
            continue
        try:
            contributed = tool.hook("loops")() or {}
        except Exception:  # noqa: BLE001
            continue
        for name, pair in contributed.items():
            out.setdefault(name, pair)
    return out


def all_specs() -> dict[str, LoopSpec]:
    return {n: s for n, (s, _) in all_loops().items()}


def all_bodies() -> dict[str, Any]:
    return {n: b for n, (_, b) in all_loops().items()}
