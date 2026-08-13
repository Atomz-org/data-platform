"""Control-plane API + dashboard. `pf ui` serves this.

Every endpoint is read-only except /api/impact (which computes) — the UI is for
tracking, not mutation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

from pf import obs
from pf.kg.impact import impact_of
from pf.kg.query import kg_neighbors, kg_path, kg_search
from pf.kg.store import open_graph
from pf.ontology.annotate import load_annotations
from pf.ontology.model import load_ontology
from pf.ontology.validate import pii_columns, validate_sources

UI_DIR = Path(__file__).parent
app = FastAPI(title="Data Platform Control Plane", version="0.1.0")


def root_dir() -> Path:
    return obs.repo_root()


def project_dir(group: str, project: str) -> Path:
    p = root_dir() / "groups" / group / "projects" / project
    if not p.exists():
        raise HTTPException(404, f"project {group}/{project} not found")
    return p


def graph_path(group: str, project: str) -> Path:
    return project_dir(group, project) / "kg" / "graph.duckdb"


# ------------------------------------------------------------------ pages --
@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (UI_DIR / "static" / "index.html").read_text()


# ---------------------------------------------------------------- topology --
@app.get("/api/tree")
def tree() -> dict[str, Any]:
    root = root_dir()
    groups_dir = root / "groups"
    out: list[dict[str, Any]] = []
    if groups_dir.exists():
        for g in sorted(p for p in groups_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            inst = g / "ontology" / "instance.yaml"
            instance = yaml.safe_load(inst.read_text()) if inst.exists() else {}
            projects = []
            pdir = g / "projects"
            if pdir.exists():
                for p in sorted(x for x in pdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
                    gp = p / "kg" / "graph.duckdb"
                    counts: dict[str, int] = {}
                    if gp.exists():
                        with open_graph(gp, read_only=True) as gr:
                            counts = gr.counts()
                    projects.append({
                        "name": p.name,
                        "is_rollup": p.name.endswith("-rollup"),
                        "counts": counts,
                        "has_graph": gp.exists(),
                        "warehouse": str(p / "data"),
                    })
            out.append({
                "name": g.name,
                "classes": instance.get("classes") or [],
                "shared_sources": instance.get("shared_sources") or [],
                "projects": projects,
            })
    return {"root": str(root), "groups": out}


@app.get("/api/summary")
def summary() -> dict[str, Any]:
    t = tree()
    n_groups = len(t["groups"])
    n_projects = sum(len(g["projects"]) for g in t["groups"])
    totals: dict[str, int] = {}
    for g in t["groups"]:
        for p in g["projects"]:
            for k, v in (p["counts"] or {}).items():
                totals[k] = totals.get(k, 0) + v
    try:
        spend = obs.query(
            'SELECT coalesce(sum(cost_usd),0) c, coalesce(sum(input_tokens+output_tokens),0) t,'
            ' count(*) n FROM agent_runs'
        )[0]
    except Exception:
        spend = {"c": 0, "t": 0, "n": 0}
    try:
        alerts = obs.query(
            "SELECT count(*) n FROM monitor_results WHERE status <> 'ok'"
        )[0]["n"]
    except Exception:
        alerts = 0
    return {
        "groups": n_groups, "projects": n_projects, "node_counts": totals,
        "agent_runs": spend["n"], "tokens": spend["t"], "cost_usd": round(spend["c"], 4),
        "open_alerts": alerts,
    }


# ---------------------------------------------------------------- ontology --
@app.get("/api/ontology")
def ontology() -> dict[str, Any]:
    o = load_ontology()
    return {
        "version": o.version,
        "classes": [
            {"name": c.name, "parent": c.parent, "abstract": c.abstract,
             "description": c.description}
            for c in o.classes.values()
        ],
        "roles": [
            {"name": r.name, "pii": r.pii, "description": r.description}
            for r in o.roles.values()
        ],
        # v1 exposed `o.edges`; v2 replaced it with named relations. Kept under
        # the old key so an existing consumer is not broken by the rename.
        "edges": [
            {"from": r.domain, "to": r.range, "type": r.name,
             "cardinality": r.cardinality}
            for r in o.relations
        ],
    }


@app.get("/api/topology")
def topology() -> dict[str, Any]:
    """Relations, policies and the evidence chain."""
    o = load_ontology()
    return {
        "version": o.version,
        "relations": [
            {"name": r.name, "domain": r.domain, "range": r.range,
             "cardinality": r.cardinality, "inverse_cardinality": r.inverse_cardinality,
             "label": r.label, "inverse": r.inverse, "description": r.description,
             "forward": r.describe(), "reverse": r.describe(reverse=True)}
            for r in o.relations
        ],
        "policies": [
            {"id": p.id, "intent": p.intent, "constraint": p.constraint,
             "severity": p.severity, "enforced_by": p.enforced_by,
             "evidence": p.evidence, "enforced": p.enforced}
            for p in o.policies
        ],
        "classes": [
            {"name": n, "identity": o.identity_of(n), "abstract": c.abstract,
             "parent": c.parent, "properties": len(o.properties_of(n))}
            for n, c in o.classes.items()
        ],
    }


@app.get("/api/mdl")
def mdl(group: str, project: str) -> dict[str, Any]:
    """The WrenAI MDL manifest projected from this project's graph."""
    from pf.projections.mdl import build_manifest
    try:
        return build_manifest(project_dir(group, project), group, project)
    except Exception as exc:  # graph not built yet
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/annotations")
def annotations(group: str, project: str) -> dict[str, Any]:
    anns = load_annotations(project_dir(group, project) / "contracts" / "annotations.yaml")
    issues = validate_sources(anns)
    return {
        "resources": [a.to_dict() for a in anns],
        "pii": [{"resource": r, "column": c, "role": ro} for r, c, ro in pii_columns(anns)],
        "issues": [
            {"severity": i.severity, "rule": i.rule, "subject": i.subject, "message": i.message}
            for i in issues
        ],
    }


# --------------------------------------------------------------------- kg --
@app.get("/api/graph")
def graph(group: str, project: str, kinds: str | None = None) -> dict[str, Any]:
    gp = graph_path(group, project)
    if not gp.exists():
        return {"nodes": [], "edges": [], "counts": {}}
    wanted = set(kinds.split(",")) if kinds else None
    with open_graph(gp, read_only=True) as g:
        nodes = [n for n in g.nodes() if not wanted or n.kind in wanted]
        ids = {n.id for n in nodes}
        edges = [e for e in g.edges() if e.src in ids and e.dst in ids]
        counts = g.counts()
    return {
        "counts": counts,
        "nodes": [{"id": n.id, "kind": n.kind, "name": n.name, "layer": n.layer,
                   "label": n.label, "props": n.props} for n in nodes],
        "edges": [{"src": e.src, "dst": e.dst, "kind": e.kind} for e in edges],
    }


@app.get("/api/kg/search")
def api_search(group: str, project: str, q: str) -> dict[str, str]:
    return {"result": kg_search(graph_path(group, project), q)}


@app.get("/api/kg/neighbors")
def api_neighbors(group: str, project: str, node: str, depth: int = 1) -> dict[str, str]:
    return {"result": kg_neighbors(graph_path(group, project), node, depth=depth)}


@app.get("/api/kg/path")
def api_path(group: str, project: str, src: str, dst: str) -> dict[str, str]:
    return {"result": kg_path(graph_path(group, project), src, dst)}


# ----------------------------------------------------------------- impact --
@app.get("/api/impact")
def api_impact(group: str, project: str, node: str, record: bool = False) -> dict[str, Any]:
    gp = graph_path(group, project)
    if not gp.exists():
        raise HTTPException(404, "graph not built — run `pf kg build`")
    try:
        report = impact_of(gp, node)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    payload = report.to_dict()
    payload["rendered"] = report.render()
    if record:
        obs.record_impact(group=group, project=project, root_node=node,
                          severity=report.severity, total=report.total, report=payload)
    return payload


# ------------------------------------------------------------ observability --
@app.get("/api/agent-runs")
def agent_runs(limit: int = 100) -> list[dict[str, Any]]:
    try:
        return obs.query(
            'SELECT id, ts, "group", project, agent, model, effort, status,'
            ' input_tokens, output_tokens, cache_read_tokens, cost_usd, duration_ms, summary'
            " FROM agent_runs ORDER BY ts DESC LIMIT ?", [limit])
    except Exception:
        return []


@app.get("/api/spend")
def spend() -> dict[str, Any]:
    try:
        by_agent = obs.query(
            'SELECT agent, model, count(*) runs, sum(input_tokens) input_tokens,'
            ' sum(output_tokens) output_tokens, sum(cache_read_tokens) cache_read,'
            ' round(sum(cost_usd),4) cost_usd'
            " FROM agent_runs GROUP BY 1,2 ORDER BY cost_usd DESC")
        by_project = obs.query(
            'SELECT "group", project, count(*) runs, round(sum(cost_usd),4) cost_usd'
            " FROM agent_runs GROUP BY 1,2 ORDER BY cost_usd DESC")
        cache = obs.query(
            'SELECT coalesce(sum(cache_read_tokens),0) reads,'
            ' coalesce(sum(input_tokens),0) fresh FROM agent_runs')[0]
    except Exception:
        by_agent, by_project, cache = [], [], {"reads": 0, "fresh": 0}
    total = (cache["reads"] or 0) + (cache["fresh"] or 0)
    return {
        "by_agent": by_agent, "by_project": by_project,
        "cache_hit_pct": round(100 * (cache["reads"] or 0) / total, 1) if total else 0.0,
    }


@app.get("/api/monitors")
def monitors(limit: int = 200) -> list[dict[str, Any]]:
    try:
        return obs.query(
            'SELECT ts, "group", project, resource, column_name, monitor, status,'
            " observed, expected, deviation_pct, message"
            " FROM monitor_results ORDER BY ts DESC LIMIT ?", [limit])
    except Exception:
        return []


@app.get("/api/pipeline-runs")
def pipeline_runs(limit: int = 200) -> list[dict[str, Any]]:
    try:
        return obs.query(
            'SELECT ts, "group", project, kind, name, status, rows, duration_ms, message'
            " FROM pipeline_runs ORDER BY ts DESC LIMIT ?", [limit])
    except Exception:
        return []


@app.get("/api/token-budgets")
def token_budgets() -> list[dict[str, Any]]:
    try:
        return obs.query(
            'SELECT ts, "group", project, artefact, tokens, budget, status'
            " FROM token_budgets ORDER BY ts DESC LIMIT 100")
    except Exception:
        return []


# ------------------------------------------------------------------ models --
@app.get("/api/models")
def models(group: str, project: str) -> list[dict[str, Any]]:
    gp = graph_path(group, project)
    if not gp.exists():
        return []
    with open_graph(gp, read_only=True) as g:
        out = []
        for m in g.nodes("Model"):
            cols = [n for n in (g.node(e.dst) for e in g.out_edges(m.id)) if n and n.kind == "Column"]
            downstream = [e.dst for e in g.out_edges(m.id) if e.kind in ("feeds", "measures")]
            out.append({
                "name": m.name, "layer": m.layer, "label": m.label,
                "grain": m.props.get("grain", ""),
                "materialized": m.props.get("materialized"),
                "columns": len(cols),
                "pii_columns": sum(1 for c in cols if c.props.get("pii")),
                "downstream": len(downstream),
                "id": m.id,
            })
    return sorted(out, key=lambda r: (r["layer"], r["name"]))


@app.get("/api/metrics")
def metrics(group: str, project: str) -> list[dict[str, Any]]:
    gp = graph_path(group, project)
    if not gp.exists():
        return []
    with open_graph(gp, read_only=True) as g:
        out = []
        for m in g.nodes("Metric"):
            upstream = [g.node(e.src) for e in g.in_edges(m.id)]
            out.append({
                "id": m.id, "name": m.name, "label": m.label,
                "type": m.props.get("type", "simple"),
                "description": m.props.get("description", ""),
                "sources": [u.name for u in upstream if u],
            })
    return sorted(out, key=lambda r: r["name"])


@app.get("/api/card")
def card(group: str, project: str) -> dict[str, Any]:
    p = project_dir(group, project) / "kg" / "context_card.md"
    text = p.read_text() if p.exists() else ""
    return {"markdown": text, "chars": len(text), "est_tokens": max(1, len(text) // 4)}


# ------------------------------------------------------------------ vendor --
# The stack a project runs on, and where each layer came from. Written here
# rather than derived, because "which upstream taught us to do X" is a judgement
# about intent that no file-level heuristic recovers.
STACK_LAYERS: list[dict[str, Any]] = [
    {"layer": "ingest", "title": "Ingest (dlt)", "upstream": "dlthub-ai-workbench",
     "toolkits": ["dlt-ingest", "dlt-explore", "dlt-quality", "dlt-performance"],
     "artefacts": "src/*/sources/*.py", "node_kinds": ["Source", "Table"]},
    {"layer": "warehouse", "title": "Warehouse (DuckDB)", "upstream": "duckdb-skills",
     "toolkits": ["duckdb-ops"], "artefacts": "data/*.duckdb", "node_kinds": []},
    {"layer": "transform", "title": "Transform (dbt)", "upstream": "dbt-agent-skills",
     "toolkits": ["dbt-modeling", "dbt-testing", "dbt-govern", "dbt-migrate"],
     "artefacts": "transform/models/**/*.sql", "node_kinds": ["Model", "Test"]},
    {"layer": "semantic", "title": "Semantic layer (MetricFlow)", "upstream": "dbt-agent-skills",
     "toolkits": ["dbt-semantic"], "artefacts": "transform/models/semantic/*",
     "node_kinds": ["Metric", "Dimension"]},
    {"layer": "orchestrate", "title": "Orchestration (Dagster)", "upstream": "dagster-skills",
     "toolkits": ["dagster-orchestrate", "python-standards"],
     "artefacts": "src/*/definitions.py", "node_kinds": []},
    {"layer": "ontology", "title": "Ontology & induction", "upstream": "context-ontology-accelerator",
     "toolkits": ["dlt-ingest"], "artefacts": "contracts/annotations.yaml",
     "node_kinds": ["Concept", "Property"]},
    {"layer": "topology", "title": "Topology & policy", "upstream": "opentopology",
     "toolkits": [], "artefacts": "governance/otop.json",
     "node_kinds": ["Relation", "Policy", "Evidence"]},
    {"layer": "mdl", "title": "MDL projection", "upstream": "wrenai",
     "toolkits": [], "artefacts": "mdl/mdl.json", "node_kinds": []},
    {"layer": "reporting", "title": "Reporting (Evidence)", "upstream": "evidence-bi",
     "toolkits": ["evidence-bi"], "artefacts": "reporting/pages/**/*.md",
     "node_kinds": ["Exposure"]},
    {"layer": "loops", "title": "Loops & governance", "upstream": "loop-engineering",
     "toolkits": [], "artefacts": "kg/context_card.md", "node_kinds": []},
]


@app.get("/api/vendor")
def vendor() -> dict[str, Any]:
    """Every vendored upstream, what we took, and whether it has drifted."""
    from pf.vendor.model import drift as vendor_drift, load_registry

    root = root_dir()
    ups = load_registry()
    by_id = {d.upstream_id: d for d in vendor_drift(root)}
    out = []
    for u in ups:
        d = by_id.get(u.id)
        out.append({
            "id": u.id, "name": u.name, "url": u.url, "path": u.path,
            "branch": u.branch, "licence": u.licence, "role": u.role,
            "why": u.why, "licence_review": u.licence_review,
            "commit": (d.current if d else ""), "locked": (d.locked if d else ""),
            "moved": bool(d and d.moved),
            "needs_review": bool(d and d.needs_review),
            "commits_behind": (d.commits_behind if d else 0),
            "severity": (d.severity if d else "none"),
            "adopted": [{"upstream": a.upstream, "kind": a.kind, "ours": a.ours,
                         "note": a.note, "severity": a.severity} for a in u.adopted],
            "declined": [{"what": x.what, "why": x.why} for x in u.declined],
            "drift": [{"path": p.path, "kind": p.kind, "state": p.state,
                       "severity": p.severity, "ours": p.ours}
                      for p in (d.paths if d else [])],
        })
    return {"upstreams": out,
            "totals": {"upstreams": len(ups),
                       "adopted": sum(len(u.adopted) for u in ups),
                       "declined": sum(len(u.declined) for u in ups),
                       "needs_review": sum(1 for r in out if r["needs_review"]),
                       "licence_review": sum(1 for r in out if r["licence_review"])}}


@app.get("/api/vendor/stack")
def vendor_stack(group: str, project: str) -> dict[str, Any]:
    """One project's stack, layer by layer, each traced to its upstream.

    This is the project-perspective view: a project owns no vendored code, but
    every layer it runs on descends from one, and the counts come from that
    project's own graph rather than from the platform.
    """
    from pf.vendor.model import drift as vendor_drift, load_registry

    d = project_dir(group, project)
    gp = d / "kg" / "graph.duckdb"
    counts: dict[str, int] = {}
    if gp.exists():
        with open_graph(gp, read_only=True) as g:
            counts = g.counts()

    ups = {u.id: u for u in load_registry()}
    drifting = {r.upstream_id for r in vendor_drift(root_dir()) if r.needs_review}

    layers = []
    for spec in STACK_LAYERS:
        u = ups.get(spec["upstream"])
        present = sum(counts.get(k, 0) for k in spec["node_kinds"])
        # Layers the graph does not model (the warehouse file, the Dagster
        # definitions, the MDL manifest) would otherwise render as a blank cell,
        # which reads as "missing" when it means "not counted here".
        files = len(list(d.glob(spec["artefacts"])))
        layers.append({
            **spec,
            "files": files,
            "upstream_name": u.name if u else spec["upstream"],
            "upstream_url": u.url if u else "",
            "licence": u.licence if u else "",
            "licence_review": bool(u and u.needs_licence_review),
            "adopted": len(u.adopted) if u else 0,
            "declined": len(u.declined) if u else 0,
            "needs_review": spec["upstream"] in drifting,
            "nodes": present,
        })
    return {"group": group, "project": project, "layers": layers, "counts": counts}


@app.get("/api/vendor/why")
def vendor_why(path: str) -> dict[str, Any]:
    from pf.vendor.model import why as lookup

    hits = lookup(root_dir(), path)
    return {"path": path, "hits": [
        {"upstream": u.id, "name": u.name, "url": u.url, "kind": a.kind,
         "upstream_path": a.upstream, "note": a.note, "ours": a.ours}
        for u, a in hits]}


@app.get("/api/otop")
def otop(group: str = "", project: str = "") -> dict[str, Any]:
    """The policy layer as an OpenTopology 0.2 manifest, with live evidence."""
    from pf.projections.otop import build_manifest

    d = project_dir(group, project) if group and project else None
    return build_manifest(root_dir(), group, project, d)


# --------------------------------------------------------------------- prs --
@app.get("/api/prs")
def prs() -> dict[str, Any]:
    """Recorded PR reports, newest first.

    Reads the same JSON that CI wrote, rather than recomputing. A dashboard that
    recomputes will eventually disagree with the comment on the PR, and then
    neither number is trusted.
    """
    from pf.pr import load_all

    return {"reports": load_all(root_dir())}


@app.post("/api/pr/refresh")
def pr_refresh(number: int = 0, base: str = "") -> dict[str, Any]:
    """Compute and record the report for the working tree. The one write here.

    Exists so the local dashboard is useful before a PR is opened — same code
    path CI runs, so what you see locally is what CI will post.
    """
    from pf.pr import build as build_pr, markdown as pr_markdown, save

    r = build_pr(root_dir(), number, base)
    save(root_dir(), r)
    payload = r.to_dict()
    payload["markdown"] = pr_markdown(r)
    return payload


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")
