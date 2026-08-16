"""Control-plane API + dashboard. `pf ui` serves this.

Read-only except for two deliberate exceptions: /api/impact computes, and
/api/governance/* writes — an ontology a data owner cannot correct is one that
drifts from the business until nobody trusts it. Every governance write leaves
an audit row before it touches a file, and the file stays the canonical artefact
that git and `pf check` still judge. See `pf.governance.store`.

## Two front ends, on purpose, for now

`/` serves the original single-file dashboard; `/app` serves the React build in
`web/`. The old page keeps working while screens move across, because a rewrite
that starts by deleting the working surface leaves the operator with nothing on
the days it is half-finished. `/app` is the one being built on.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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


DIST = UI_DIR / "static" / "dist"

# Mounted *before* the /app catch-all below, and only when built.
#
# Order is load-bearing: routes match in declaration order, so a catch-all
# declared first swallows `/app/assets/index.js` and answers it with the HTML
# shell. The browser then refuses to execute a module served as text/html — and
# does so silently, with no console error, leaving a blank page and no clue.
# Mounting a missing directory raises at import time, which would take the API
# down over an unbuilt front end, hence the guard.
if (DIST / "assets").exists():
    app.mount("/app/assets",
              StaticFiles(directory=str(DIST / "assets")), name="assets")


@app.get("/app", response_class=HTMLResponse)
@app.get("/app/{path:path}", response_class=HTMLResponse)
def spa(path: str = "") -> str:
    """The React control plane. Every route returns the shell; routing is client
    side, so a deep link that the server has never heard of still resolves."""
    entry = DIST / "index.html"
    if not entry.exists():
        raise HTTPException(
            503, "UI not built — run `npm --prefix platform/src/pf/ui/web run build`")
    return entry.read_text()


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

    # Tool-contributed layers append to the hand-written stack rather than being
    # listed in it: a tool installed from outside this repo has to be able to
    # appear here, and STACK_LAYERS is a file in this repo.
    from pf.tools import stack_layers as tool_stack_layers

    layers = []
    for spec in [*STACK_LAYERS, *tool_stack_layers()]:
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


# ------------------------------------------------------------- operations --
@app.get("/api/health")
def health() -> dict[str, Any]:
    """Which parts of the platform are actually up, for the shell's footer.

    Each row is probed, not assumed. "All services running" that is hardcoded is
    worse than no indicator, because it is believed.
    """
    root = root_dir()
    services: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        services.append({"name": name, "ok": ok, "detail": detail})

    try:
        n = len(obs.query("SELECT 1 FROM pipeline_runs LIMIT 1"))
        add("tracking db", True, "duckdb" if n >= 0 else "")
    except Exception as exc:  # noqa: BLE001
        add("tracking db", False, str(exc)[:80])

    ws = root / "platform" / "workspace.yaml"
    locations = ws.read_text().count("python_module:") if ws.exists() else 0
    add("dagster workspace", ws.exists(), f"{locations} code location(s)")

    gate = root / "gate.yaml"
    add("safety gate", gate.exists(), "denylist present" if gate.exists() else "missing")

    try:
        from pf.tools import all_tools

        tools = all_tools()
        installed = [n for n, t in tools.items() if t.installed]
        add("tools", True, f"{len(installed)}/{len(tools)} installed")
    except Exception as exc:  # noqa: BLE001
        add("tools", False, str(exc)[:80])

    return {"ok": all(s["ok"] for s in services), "services": services}


@app.get("/api/activity")
def activity(group: str = "", project: str = "", limit: int = 40) -> list[dict[str, Any]]:
    """One feed over every kind of thing that happened, newest first.

    The obs tables are separate because they record different shapes, but an
    operator does not think in tables — they think "what happened here lately".
    Unioning at read time keeps the writers simple and the reading useful.
    """
    where = ""
    params: list[Any] = []
    if group and project:
        where = ' WHERE "group" = ? AND project = ?'
        params = [group, project]

    def rows(sql: str, extra: list[Any] | None = None) -> list[dict[str, Any]]:
        try:
            return obs.query(sql, (params + (extra or [])) if params or extra else None)
        except Exception:  # noqa: BLE001 — a missing table is an empty feed
            return []

    out: list[dict[str, Any]] = []
    for r in rows(f'SELECT ts, "group", project, kind, name, status, message'
                  f" FROM pipeline_runs{where} ORDER BY ts DESC LIMIT 25", []):
        out.append({"ts": str(r["ts"]), "group": r["group"], "project": r["project"],
                    "kind": "pipeline", "verb": f"ran {r['kind']}",
                    "subject": r["name"], "status": r["status"],
                    "detail": (r["message"] or "")[:120]})
    for r in rows(f'SELECT ts, "group", project, root_node, severity, total'
                  f" FROM impact_reports{where} ORDER BY ts DESC LIMIT 15", []):
        out.append({"ts": str(r["ts"]), "group": r["group"], "project": r["project"],
                    "kind": "impact", "verb": "assessed blast radius",
                    "subject": r["root_node"],
                    "status": {"breaking": "error", "review": "warn"}.get(
                        r["severity"], "ok"),
                    "detail": f"{r['total']} downstream object(s)"})
    for r in rows(f'SELECT ts, "group", project, resource, column_name, monitor, status,'
                  f" message FROM monitor_results{where}"
                  f" AND status <> 'ok' ORDER BY ts DESC LIMIT 15"
                  if where else
                  "SELECT ts, \"group\", project, resource, column_name, monitor, status,"
                  " message FROM monitor_results WHERE status <> 'ok'"
                  " ORDER BY ts DESC LIMIT 15", []):
        out.append({"ts": str(r["ts"]), "group": r["group"], "project": r["project"],
                    "kind": "monitor", "verb": f"{r['monitor']} on",
                    "subject": f"{r['resource']}.{r['column_name']}",
                    "status": "error" if r["status"] == "critical" else "warn",
                    "detail": (r["message"] or "")[:120]})
    for r in rows(f'SELECT ts, "group", project, agent, model, status, cost_usd, summary'
                  f" FROM agent_runs{where} ORDER BY ts DESC LIMIT 15", []):
        out.append({"ts": str(r["ts"]), "group": r["group"], "project": r["project"],
                    "kind": "agent", "verb": f"{r['agent']} ran",
                    "subject": r["model"],
                    "status": "ok" if r["status"] in ("ok", "success") else "warn",
                    "detail": (r["summary"] or "")[:120]})

    out.sort(key=lambda r: r["ts"], reverse=True)
    return out[:limit]


@app.get("/api/timeseries")
def timeseries(group: str = "", project: str = "", hours: int = 48) -> dict[str, Any]:
    """Pipeline outcomes bucketed by hour.

    Two separate series returned, never combined into one plot: a success *rate*
    (percent) and a failure *count* are different units, and putting them on one
    pair of axes is the most common chart mistake there is. The UI renders them
    as two panels sharing an x-axis.
    """
    where = ""
    params: list[Any] = []
    if group and project:
        where = ' AND "group" = ? AND project = ?'
        params = [group, project]
    sql = (
        "SELECT date_trunc('hour', ts) AS bucket,"
        " count(*) AS total,"
        " sum(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS ok,"
        " sum(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS failed"
        " FROM pipeline_runs"
        f" WHERE ts >= now() - INTERVAL '{int(hours)} hours'{where}"
        " GROUP BY 1 ORDER BY 1"
    )
    try:
        rows = obs.query(sql, params or None)
    except Exception:  # noqa: BLE001
        rows = []
    points = []
    for r in rows:
        total = r["total"] or 0
        ok = r["ok"] or 0
        points.append({
            "t": str(r["bucket"]),
            "total": total,
            "failed": r["failed"] or 0,
            # A bucket with no runs has no rate; null makes the line break
            # rather than drawing a dip to zero that never happened.
            "rate": round(100.0 * ok / total, 1) if total else None,
        })
    return {"points": points, "hours": hours}


# ------------------------------------------------------------------- wren --
@app.get("/api/wren/mdl")
def wren_mdl(group: str, project: str) -> dict[str, Any]:
    """This project's semantic layer, read from the manifest we export."""
    from pf.tools.wren import probe_engine, summarise_mdl

    d = project_dir(group, project)
    return {**summarise_mdl(d), "engine": probe_engine()}


@app.post("/api/wren/plan")
def wren_plan(group: str, project: str, sql: str = Query(...)) -> dict[str, Any]:
    """Expand SQL through the MDL. No warehouse access, so it is safe to expose."""
    from pf.tools.wren import plan

    return plan(project_dir(group, project), sql)


@app.post("/api/wren/query")
def wren_query(group: str, project: str, sql: str = Query(...),
               limit: int = 200) -> dict[str, Any]:
    """Answer a question through the semantic layer.

    Read-only by construction: the warehouse is opened `read_only=True` in
    `pf.tools.wren.query`, so this endpoint cannot write whatever it is handed.
    """
    from pf.tools.wren import query

    return query(project_dir(group, project), sql, limit=limit)


# ------------------------------------------------------------------- tools --
@app.get("/api/tools")
def tools(group: str = "", project: str = "") -> dict[str, Any]:
    """Every registered tool, with this project's enablement and readiness.

    The UI never names a tool. This endpoint is the whole reason the Review tab
    can show Recce today and something else tomorrow without a front-end change.
    """
    from pf.tools import discover, readiness, stack_layers

    found, errors = discover()
    rows: list[dict[str, Any]] = []
    if group and project:
        project_dir(group, project)  # 404s if the project does not exist
        rows = readiness(root_dir(), group, project)
    else:
        rows = [{
            "name": n, "title": t.title, "summary": t.summary, "url": t.url,
            "scope": sorted(t.scope), "enabled": False, "source": "—",
            "installed": t.installed,
            "missing": [m.describe() for m in t.missing()],
            "hint": next((m.hint for m in t.missing() if m.hint), ""),
            "surface": t.surface.url() if t.surface else "",
            "embeddable": bool(t.surface and t.surface.embeddable),
            "blockers": [], "ready": False,
        } for n, t in sorted(found.items())]

    return {
        "tools": rows,
        "layers": stack_layers(),
        "errors": [str(e) for e in errors],
    }


@app.get("/api/tools/surface")
def tool_surface(tool: str, group: str = "", project: str = "") -> dict[str, Any]:
    """Is this tool's own UI actually up, and may we embed it?

    Probed rather than assumed. An iframe pointed at a server that is not
    running renders an unexplained blank rectangle, and the operator has no way
    to tell that apart from a tool that is broken. Knowing it is down lets the
    page say so and print the command that starts it.
    """
    import socket
    from urllib.parse import urlparse

    from pf.tools import get as get_tool
    from pf.tools.spec import InvalidTool

    try:
        t = get_tool(tool)
    except InvalidTool as exc:
        raise HTTPException(404, str(exc)) from exc
    if t.surface is None:
        return {"tool": tool, "surface": "", "up": False, "embeddable": False,
                "start_hint": ""}

    url = t.surface.url()
    parsed = urlparse(url)
    up = False
    try:
        with socket.create_connection(
                (parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=0.4):
            up = True
    except OSError:
        up = False
    hint = (f"pf tool {tool} serve {group} {project}".rstrip()
            if group and project else f"pf tool {tool} serve <group> <project>")
    return {"tool": tool, "surface": url, "up": up,
            "embeddable": t.surface.embeddable, "installed": t.installed,
            "start_hint": hint}


@app.get("/api/tools/recce")
def recce_state(group: str, project: str) -> dict[str, Any]:
    """The recorded diff for this project, if a review has been run.

    Reads the state file rather than recomputing, for the same reason /api/prs
    does: a dashboard that recomputes will eventually disagree with the run that
    produced the number, and then neither is trusted.

    Fetches it once if it is not there. The state file is no longer in git, so
    on a fresh clone "not there" is the *normal* state of a project that has
    been reviewed — and a panel that renders empty because nobody ran
    `pf artifacts pull` looks exactly like a panel that renders empty because
    the review found nothing. Recomputing is still refused; downloading the
    recorded answer is not recomputing it.
    """
    from pf import artifacts
    from pf.tools.recce import (
        fetch_review, has_baseline, has_manifest, read_state, state_file,
        summary_markdown,
    )

    d = project_dir(group, project)
    fetched = ""
    if not state_file(d).exists() and artifacts.Store.from_env() is not None:
        try:
            if any(t.ok for t in fetch_review(d, group, project)):
                fetched = "store"
        except artifacts.ArtifactStoreError as exc:
            # A dashboard panel is not the place to fail a request over a
            # bucket. Report it in the payload so the UI can say why the panel
            # is empty instead of implying the review was clean.
            fetched = f"error: {exc}"
    return {
        "group": group, "project": project,
        "has_manifest": has_manifest(d),
        "has_baseline": has_baseline(d),
        "summary_markdown": summary_markdown(d),
        "fetched_from": fetched,
        **read_state(d),
    }


@app.get("/api/workspace/semantic-diff")
def semantic_diff(group: str, project: str) -> dict[str, Any]:
    """The review and the semantic layer as one table, joined on the relation.

    Recce says a dbt model moved. Wren says which semantic entity that model
    backs, and which ontology roles ride on it. Separately they are two panels
    an operator reads and correlates by eye; the question actually being asked —
    *does this change reach anything a consumer sees?* — is the join, so the
    join is what gets served.

    The control plane owns it because it is the only layer that knows both tools
    are on. Putting it in either tool would make two independently installable
    plugins import each other, which is the coupling `pf.tools` exists to avoid.
    Either side may be absent: a project with no MDL still gets its diff rows,
    and a project that has never been reviewed still gets its semantic layer,
    each labelled with what is missing rather than rendered as a clean result.
    """
    from pf.tools import enabled_names
    from pf.tools.recce import has_baseline, model_diffs
    from pf.tools.wren import summarise_mdl

    d = project_dir(group, project)
    on = set(enabled_names(root_dir(), group, project))
    mdl = summarise_mdl(d) if "wren" in on else {"models": []}
    diffs = model_diffs(d) if "recce" in on else {}
    reviewed = bool(diffs)

    rows: list[dict[str, Any]] = []
    for m in mdl.get("models") or []:
        # Join on the dbt model name. `tableReference.table` is the same string
        # for a dbt-built relation, but it is the *warehouse* name and a rename
        # would break the join silently, so the semantic name leads and the
        # table is the fallback.
        d_row = diffs.get(m["name"]) or diffs.get(m.get("table") or "") or {}
        rows.append({
            **m,
            "status": ("unreviewed" if not reviewed
                       else "moved" if d_row.get("moved")
                       else "held" if d_row else "uncovered"),
            "checks": d_row.get("checks", 0),
            "check_types": d_row.get("check_types", []),
            "row_count": d_row.get("row_count"),
            "rows_added": d_row.get("rows_added", 0),
            "rows_removed": d_row.get("rows_removed", 0),
            "categories_drifted": d_row.get("categories_drifted", []),
        })

    # A model recce measured that the semantic layer does not expose. Not an
    # error — staging models are reviewed and deliberately not published — but
    # worth showing, because the alternative is a changed model that silently
    # appears in no list on this page.
    named = {r["name"] for r in rows} | {r.get("table") for r in rows}
    unpublished = [
        {**v, "check_types": v.get("check_types", [])}
        for k, v in sorted(diffs.items()) if k not in named
    ]

    counts = {s: sum(1 for r in rows if r["status"] == s)
              for s in ("moved", "held", "uncovered", "unreviewed")}
    return {
        "group": group, "project": project,
        "wren_enabled": "wren" in on, "recce_enabled": "recce" in on,
        "reviewed": reviewed, "has_baseline": has_baseline(d) if "recce" in on else False,
        "catalog": mdl.get("catalog", ""), "schema": mdl.get("schema", ""),
        "models": rows, "unpublished": unpublished, "counts": counts,
    }


@app.get("/api/tools/recce/checks")
def recce_checks(group: str, project: str) -> dict[str, Any]:
    """Every recorded check and what it found.

    The counts were always here; the findings were not, and lived only inside
    Recce's own server. A review nobody can read without starting a second
    process is a review that gets skipped.
    """
    from pf.tools.recce import check_results

    rows = check_results(project_dir(group, project))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    return {"group": group, "project": project, "checks": rows, "counts": counts}


# ------------------------------------------------------------- governance --
@app.get("/api/governance/surfaces")
def governance_surfaces() -> dict[str, Any]:
    from pf.governance import surfaces

    return {"surfaces": surfaces()}


@app.get("/api/governance/document")
def governance_document(surface: str, group: str = "") -> dict[str, Any]:
    from pf.governance import EditRejected, current

    try:
        return current(surface, root_dir(), group)
    except EditRejected as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/governance/history")
def governance_history(surface: str = "", group: str = "",
                       limit: int = 200) -> dict[str, Any]:
    from pf.governance import history

    return {"edits": history(root_dir(), surface, group, limit)}


@app.post("/api/governance/edit")
def governance_edit(surface: str = Query(...), key_path: str = Query(...),
                    value: str = Query(...), actor: str = Query(...),
                    reason: str = Query(""), group: str = Query(""),
                    ) -> dict[str, Any]:
    """Apply one owner edit: audit row first, then the YAML.

    `actor` is required and not defaulted. An audit trail whose author column can
    be blank records that something changed and nothing about who decided it,
    which is the only part that matters when the definition is later disputed.
    """
    from pf.governance import EditRejected, apply_edit

    parsed: Any = value
    if value.lower() in {"true", "false"}:
        parsed = value.lower() == "true"
    else:
        try:
            parsed = int(value)
        except ValueError:
            pass

    try:
        return apply_edit(root_dir(), surface, key_path, parsed,
                          actor=actor, reason=reason, group=group)
    except EditRejected as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/governance/revert")
def governance_revert(edit_id: str = Query(...),
                      actor: str = Query(...)) -> dict[str, Any]:
    from pf.governance import EditRejected, revert

    try:
        return revert(root_dir(), edit_id, actor=actor)
    except EditRejected as exc:
        raise HTTPException(400, str(exc)) from exc


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
