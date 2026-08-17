"""Consolidated MCP server, scoped to the active project by cwd.

Tool surface merges four upstream sources:
  dlt AI Workbench   list_tables, preview_table, execute_sql_query, get_row_counts,
                     display_schema, get_local_pipeline_state, secrets_view_redacted,
                     secrets_update_fragment, list_toolkits, toolkit_info
  dbt MCP (Core mode) dbt_list, dbt_build, dbt_test, dbt_compile, get_model_details
  MetricFlow          list_metrics, query_metrics, get_dimensions
  this platform       kg_search, kg_neighbors, kg_path, impact_analysis,
                      ontology_classes, validate_annotations

TRUNCATION POLICY (applies to every data-returning tool): schema + <=20 sample
rows + summary stats. Never a raw dump. This is the single cheapest defence
against context blowups.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from pf import obs
from pf.kg.impact import impact_of
from pf.kg.query import kg_neighbors, kg_path, kg_search
from pf.ontology.annotate import load_annotations
from pf.ontology.model import load_ontology
from pf.ontology.validate import validate_sources
from pf.runtime.warehouse import Warehouse, preview

MAX_ROWS = 20
MAX_CHARS = 8000
SECRET_RE = re.compile(r"(password|token|secret|api_key|key|credential)\s*=\s*.+", re.I)


# --------------------------------------------------------------- context --
def active_project() -> tuple[str, str, Path]:
    """Resolve group/project from cwd. Isolation lives here."""
    cwd = Path(os.environ.get("PF_PROJECT_DIR", Path.cwd())).resolve()
    for p in [cwd, *cwd.parents]:
        if p.parent.name == "projects" and (p.parent.parent / "ontology").exists():
            return p.parent.parent.name, p.name, p
    raise RuntimeError(
        "not inside a project — run from groups/<group>/projects/<project> "
        "or set PF_PROJECT_DIR"
    )


def _wh() -> Warehouse:
    group, project, root = active_project()
    return Warehouse.for_project(root, group, project)


def _clip(text: str, limit: int = MAX_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… truncated ({len(text)} chars)"


# ------------------------------------------------------- dlt / warehouse --
def list_tables() -> str:
    """List every table in the project warehouse with row counts."""
    with _wh().connect(read_only=True) as con:
        rows = con.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema','pg_catalog') "
            "ORDER BY 1,2"
        ).fetchall()
        out = []
        for schema, name in rows:
            try:
                n = con.execute(f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
            except Exception:
                n = -1
            out.append(f"  {schema}.{name}  ({n:,} rows)")
    return f"{len(rows)} table(s):\n" + "\n".join(out) if rows else "No tables loaded yet."


def preview_table(table: str, limit: int = 5) -> str:
    """Schema + sample rows + row count for one table. Never dumps the table."""
    with _wh().connect(read_only=True) as con:
        info = preview(con, table, min(limit, MAX_ROWS))
    lines = [f"{info['table']} — {info['row_count']:,} rows",
             "columns: " + ", ".join(f"{c['name']}:{c['type']}" for c in info["columns"]),
             f"sample ({len(info['sample'])} of {info['row_count']:,}):"]
    for r in info["sample"]:
        lines.append("  " + " | ".join(str(v)[:40] for v in r))
    if info["truncated"]:
        lines.append("  … truncated by policy; use execute_sql_query to aggregate")
    return _clip("\n".join(lines))


def execute_sql_query(sql: str, limit: int = MAX_ROWS) -> str:
    """Read-only ad-hoc SQL. Prefer query_metrics for anything with a definition."""
    if re.search(r"\b(insert|update|delete|drop|create|alter|attach|copy)\b", sql, re.I):
        return "Refused: this tool is read-only. Use a dbt model or a Dagster asset to write."
    with _wh().connect(read_only=True) as con:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(min(limit, MAX_ROWS) + 1)
    truncated = len(rows) > min(limit, MAX_ROWS)
    rows = rows[:min(limit, MAX_ROWS)]
    out = [" | ".join(cols), "-" * 40]
    out += [" | ".join(str(v)[:40] for v in r) for r in rows]
    if truncated:
        out.append(f"… more rows exist; capped at {min(limit, MAX_ROWS)} by policy")
    return _clip("\n".join(out))


def get_row_counts() -> str:
    """Row counts for every table — the cheapest freshness signal."""
    return list_tables()


def display_schema(table: str) -> str:
    """Column names and types for one table."""
    with _wh().connect(read_only=True) as con:
        rows = con.execute(f"DESCRIBE SELECT * FROM {table}").fetchall()
    return "\n".join(f"  {r[0]}: {r[1]}" for r in rows)


def get_local_pipeline_state() -> str:
    """dlt pipeline state for this project (last load ids, schema versions)."""
    _, project, _root = active_project()
    states = sorted(Path.home().joinpath(".dlt", "pipelines").glob(f"{project}_*"))
    if not states:
        return "No local dlt pipeline state found. Run the ingest assets first."
    out = []
    for s in states:
        f = s / "state.json"
        if f.exists():
            st = json.loads(f.read_text())
            out.append(f"  {s.name}: schema v{st.get('_version', '?')} "
                       f"dataset={st.get('dataset_name')}")
        else:
            out.append(f"  {s.name}: (no state.json)")
    return "\n".join(out)


# ----------------------------------------------------------- secrets ------
def secrets_view_redacted() -> str:
    """Show secrets files with values masked. Never returns raw credentials."""
    _, _, root = active_project()
    out = []
    for f in [root / ".dlt" / "secrets.toml", root / ".env"]:
        if not f.exists():
            continue
        out.append(f"--- {f} ---")
        for line in f.read_text().splitlines():
            out.append(SECRET_RE.sub(lambda m: m.group(0).split("=")[0] + "= ***REDACTED***", line))
    return "\n".join(out) or "No secrets files found."


def secrets_update_fragment(toml_fragment: str, path: str = ".dlt/secrets.toml") -> str:
    """Merge a TOML fragment into a secrets file. The agent never reads it back."""
    _, _, root = active_project()
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text() if target.exists() else ""
    target.write_text(existing.rstrip() + "\n" + toml_fragment.strip() + "\n")
    return f"Merged {len(toml_fragment)} chars into {path}. Values are not echoed."


# ---------------------------------------------------------------- dbt -----
def dbt_list(select: str = "") -> str:
    """List dbt resources, optionally with a selector."""
    from pf.runtime.dbt_runtime import dbt
    _, _, root = active_project()
    args = ["ls", "--output", "name"] + (["--select", select] if select else [])
    proc = dbt(root, *args, duckdb_path=_wh().path)
    return _clip(proc.stdout or proc.stderr)


def dbt_build(select: str = "") -> str:
    """Run dbt build, optionally scoped by selector."""
    from pf.runtime.dbt_runtime import dbt, failed_nodes
    _, _, root = active_project()
    args = ["build"] + (["--select", select] if select else [])
    proc = dbt(root, *args, duckdb_path=_wh().path)
    fails = failed_nodes(root)
    tail = proc.stdout[-3000:]
    return f"exit={proc.returncode}, {len(fails)} failure(s)\n{tail}"


def dbt_test(select: str = "") -> str:
    """Run dbt tests."""
    from pf.runtime.dbt_runtime import dbt
    _, _, root = active_project()
    args = ["test"] + (["--select", select] if select else [])
    proc = dbt(root, *args, duckdb_path=_wh().path)
    return _clip(proc.stdout[-4000:])


def get_model_details(model: str) -> str:
    """Compiled SQL, columns, grain and tests for one dbt model."""
    from pf.runtime.dbt_runtime import manifest
    _, _, root = active_project()
    m = manifest(root)
    for _uid, node in (m.get("nodes") or {}).items():
        if node.get("resource_type") == "model" and node.get("name") == model:
            cols = ", ".join((node.get("columns") or {}).keys())
            return (f"{model} ({node.get('config', {}).get('materialized')})\n"
                    f"schema: {node.get('schema')}\n"
                    f"grain: {(node.get('meta') or {}).get('grain', 'undeclared')}\n"
                    f"description: {node.get('description', '')}\n"
                    f"columns: {cols}\n\n"
                    f"{_clip(node.get('raw_code', ''), 3000)}")
    return f"Model '{model}' not found in the manifest. Run `dbt parse` first."


# --------------------------------------------------------- metricflow -----
def list_metrics() -> str:
    """Every governed metric. Start here for any business question."""
    _, _, root = active_project()
    sm = root / "transform" / "target" / "semantic_manifest.json"
    if not sm.exists():
        return "No semantic manifest. Run `dbt parse` in transform/."
    payload = json.loads(sm.read_text())
    lines = []
    for m in payload.get("metrics") or []:
        lines.append(f"  {m['name']} ({m.get('type')}) — {m.get('label') or m.get('description') or ''}")
    return f"{len(lines)} metric(s):\n" + "\n".join(lines) if lines else "No metrics defined."


def get_dimensions(metrics: list[str]) -> str:
    """Dimensions available for the given metrics."""
    _, _, root = active_project()
    proc = subprocess.run(
        ["mf", "list", "dimensions", "--metrics", ",".join(metrics)],
        cwd=str(root / "transform"), capture_output=True, text=True)
    return _clip(proc.stdout or proc.stderr)


def query_metrics(metrics: list[str], group_by: list[str] | None = None,
                  where: str = "", limit: int = 100) -> str:
    """Query governed business metrics. PREFER THIS over raw SQL.

    Args:
        metrics: metric names from list_metrics, e.g. ["revenue", "aov"].
        group_by: dimensions, e.g. ["metric_time__month", "customer__segment"].
        where: optional MetricFlow filter expression.
        limit: max rows returned.
    """
    from pf.runtime.dbt_runtime import mf_query
    _, _, root = active_project()
    proc = mf_query(root, metrics, group_by or [], where, min(limit, 200))
    if proc.returncode != 0:
        return (f"MetricFlow error:\n{_clip(proc.stderr, 2000)}\n\n"
                f"If no metric covers the question, say which definition is missing "
                f"rather than falling back to raw SQL silently.")
    return _clip(proc.stdout)


# ------------------------------------------------------------- graph ------
def _graph_path() -> Path:
    _, _, root = active_project()
    return root / "kg" / "graph.duckdb"


def kg_search_tool(term: str, kinds: list[str] | None = None) -> str:
    """Find nodes by name, label or business term. The vague-question entry point."""
    return kg_search(_graph_path(), term, kinds)


def kg_neighbors_tool(node: str, depth: int = 1, kinds: list[str] | None = None) -> str:
    """Explore the graph around a node. Call this BEFORE reading any file."""
    return kg_neighbors(_graph_path(), node, depth=depth, kinds=kinds)


def kg_path_tool(src: str, dst: str) -> str:
    """Shortest lineage path — how does a source column reach a metric?"""
    return kg_path(_graph_path(), src, dst)


def impact_analysis(node: str) -> str:
    """Blast radius of changing a node. Run before any schema or model change."""
    group, project, _ = active_project()
    report = impact_of(_graph_path(), node)
    obs.record_impact(group=group, project=project, root_node=node,
                      severity=report.severity, total=report.total,
                      report=report.to_dict())
    return report.render()


# ---------------------------------------------------------- ontology ------
def ontology_classes() -> str:
    """The shared business vocabulary this platform models against."""
    o = load_ontology()
    lines = [f"  {n}{' (abstract)' if c.abstract else ''}"
             f"{' < ' + c.parent if c.parent else ''} — {c.description}"
             for n, c in o.classes.items()]
    roles = ", ".join(o.roles)
    return "Classes:\n" + "\n".join(lines) + f"\n\nColumn roles: {roles}"


def validate_annotations() -> str:
    """Check this project's dlt annotations against the ontology and topology."""
    _, _, root = active_project()
    anns = load_annotations(root / "contracts" / "annotations.yaml")
    if not anns:
        return "No annotations exported. Run the ingest assets or `pf seed`."
    issues = validate_sources(anns)
    if not issues:
        return f"✅ {len(anns)} resource(s) conform to the ontology."
    return f"{len(issues)} issue(s):\n" + "\n".join(f"  {i}" for i in issues)


# --------------------------------------------------------- toolkits -------
def list_toolkits() -> str:
    """Installed platform toolkits (skills available to this session)."""
    root = obs.repo_root()
    tdir = root / "platform" / "toolkits"
    if not tdir.exists():
        return "No toolkits directory."
    out = []
    for t in sorted(p for p in tdir.iterdir() if p.is_dir()):
        skills = sorted(s.name for s in (t / "skills").iterdir()) if (t / "skills").exists() else []
        out.append(f"  {t.name}: {', '.join(skills) or '(rules only)'}")
    return "\n".join(out)


def toolkit_info(name: str) -> str:
    """Rules and skills for one toolkit."""
    root = obs.repo_root()
    t = root / "platform" / "toolkits" / name
    if not t.exists():
        return f"Toolkit '{name}' not found. Use list_toolkits."
    rules = (t / "RULES.md").read_text() if (t / "RULES.md").exists() else ""
    skills = sorted(s.name for s in (t / "skills").iterdir()) if (t / "skills").exists() else []
    return f"# {name}\nskills: {', '.join(skills)}\n\n{_clip(rules, 3000)}"


TOOLS = {
    "list_tables": list_tables,
    "preview_table": preview_table,
    "execute_sql_query": execute_sql_query,
    "get_row_counts": get_row_counts,
    "display_schema": display_schema,
    "get_local_pipeline_state": get_local_pipeline_state,
    "secrets_view_redacted": secrets_view_redacted,
    "secrets_update_fragment": secrets_update_fragment,
    "dbt_list": dbt_list,
    "dbt_build": dbt_build,
    "dbt_test": dbt_test,
    "get_model_details": get_model_details,
    "list_metrics": list_metrics,
    "get_dimensions": get_dimensions,
    "query_metrics": query_metrics,
    "kg_search": kg_search_tool,
    "kg_neighbors": kg_neighbors_tool,
    "kg_path": kg_path_tool,
    "impact_analysis": impact_analysis,
    "ontology_classes": ontology_classes,
    "validate_annotations": validate_annotations,
    "list_toolkits": list_toolkits,
    "toolkit_info": toolkit_info,
}

# Hot tools stay loaded; the rest are deferred so their schemas do not ride in
# every request. Pair with the tool-search tool on the client side.
HOT_TOOLS = ("kg_search", "kg_neighbors", "query_metrics", "impact_analysis", "list_tables")


def main() -> None:
    """Run as a stdio MCP server (requires the `mcp` extra)."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("pf-platform")
    for name, fn in TOOLS.items():
        server.add_tool(fn, name=name, description=(fn.__doc__ or "").strip())
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
