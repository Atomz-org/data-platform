"""Wren — the semantic layer projected out, and queried back.

The platform already emits a conformant MDL manifest (`pf.projections.mdl`), and
the vendor registry has said for a while that adopting Wren "means pointing it at
`mdl/mdl.json`, with nothing else to change". This module is that pointing —
and the place where the claim finally gets tested rather than asserted.

## What Wren is now, and what it is not

Upstream changed shape. The Docker-based chat-first BI product with a web UI is
`legacy/v1`, archived and renamed "Wren GenBI Classic". Current WrenAI is
**agent-driven**: a CLI over MDL, a skills bundle, and `wren serve` — which
serves **MCP**, not a web page.

So there is no Wren UI to embed, and this tool declares **no `Surface`**. That is
not a gap in the integration; it is the integration being honest about upstream.
The semantic surface a person actually looks at is ours — the control plane reads
the same `mdl/mdl.json` and renders it — which is the right split anyway: we own
our UI, and we do not iframe something that no longer exists.

## Why there is an engine probe

`Requirement` answers "is it installed". For Wren that is not the same as "does
it work", and the probe earned its place by catching a real failure: every query
touching a model died with `[INVALID_SQL] interpreted classes cannot inherit
from compiled`.

That was read here for a while as a broken upstream binary. It was not. Wren
registers its own `wren` sqlglot dialect by subclassing sqlglot's Parser in pure
Python, and `sqlglotc` — the Cython build, pulled in by `dagster-dbt` asking for
`sqlglot[rs]` — makes that base class uninheritable. Two tools that never
reference each other, one environment, and a semantic layer that could not answer
a question. The `[tool.uv] override-dependencies` entry in the root
`pyproject.toml` is the fix; this note is here because the error message says
INVALID_SQL and points at the manifest, which is the wrong place to look.

`probe_engine()` still runs the check, because the next such conflict will not
announce itself either.

## Who executes

Wren plans; the warehouse connection stays ours. See `query()` — Wren's `duckdb`
datasource is a file scanner with no concept of dbt's schemas, so the planning is
taken and the execution is not.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pf.capabilities import Capability
from pf.tools.spec import DbtBinding, Requirement, Tool, ToolContext, ToolContribution

MDL_REL = "mdl/mdl.json"
CONNECTION_REL = "mdl/connection.json"

# A manifest with one model and one column — the smallest thing that still makes
# the planner resolve a model. If this cannot plan, nothing can, and the cause is
# upstream rather than anything this platform emitted.
PROBE_MDL: dict[str, Any] = {
    "catalog": "probe", "schema": "probe", "dataSource": "DUCKDB",
    "layoutVersion": 1,
    "models": [{"name": "t", "tableReference": {"schema": "main", "table": "t"},
                "columns": [{"name": "a", "type": "VARCHAR", "isCalculated": False,
                             "notNull": False, "isHidden": False}]}],
    "relationships": [], "views": [], "metrics": [],
}


# ------------------------------------------------------------------ paths --
def mdl_path(project_dir: Path) -> Path:
    return Path(project_dir) / MDL_REL


def connection_path(project_dir: Path) -> Path:
    return Path(project_dir) / CONNECTION_REL


def has_mdl(project_dir: Path) -> bool:
    return mdl_path(project_dir).exists()


def _wren(*args: str, cwd: Path | None = None,
          timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["wren", *args], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=timeout)


# ------------------------------------------------------------- connection --
def write_connection(project_dir: Path, project: str = "") -> tuple[Path, bool]:
    """Write the datasource stanza the CLI needs. Idempotent.

    `wren` refuses every command without a `datasource` key, including the ones
    that never touch a database — so this is written even for plan-only use.
    """
    from pf.runtime.warehouse import Warehouse

    d = Path(project_dir)
    wh = Warehouse.for_project(d, d.parents[1].name if len(d.parents) >= 2 else "",
                               project or d.name)
    body = json.dumps({"datasource": "duckdb", "path": str(wh.path)}, indent=2) + "\n"
    path = connection_path(d)
    if path.exists() and path.read_text() == body:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path, True


# ----------------------------------------------------------------- probe --
def probe_engine() -> dict[str, Any]:
    """Can this install plan a query against *any* MDL? Cached per process.

    Returns {ok, detail}. Never raises — an unusable engine is a finding to
    report, not an exception to propagate into the UI or the doctor.
    """
    if getattr(probe_engine, "_cache", None) is not None:
        return probe_engine._cache  # type: ignore[attr-defined]

    result: dict[str, Any] = {"ok": False, "detail": ""}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            m = Path(tmp) / "mdl.json"
            c = Path(tmp) / "conn.json"
            m.write_text(json.dumps(PROBE_MDL))
            c.write_text(json.dumps({"datasource": "duckdb"}))
            proc = _wren("dry-plan", "--sql", "select a from t",
                         "--mdl", str(m), "--connection-file", str(c), timeout=60)
        if proc.returncode == 0:
            result = {"ok": True, "detail": "planner resolves models"}
        else:
            msg = (proc.stderr or proc.stdout or "").strip().splitlines()
            result = {"ok": False,
                      "detail": (msg[-1] if msg else "dry-plan failed")[:200]}
    except FileNotFoundError:
        result = {"ok": False, "detail": "wren not on PATH"}
    except Exception as exc:  # noqa: BLE001 — a broken probe is still a finding
        result = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"[:200]}

    probe_engine._cache = result  # type: ignore[attr-defined]
    return result


# ------------------------------------------------------------------ query --
def plan(project_dir: Path, sql: str) -> dict[str, Any]:
    """Expand SQL through the MDL without touching the warehouse."""
    d = Path(project_dir)
    if not has_mdl(d):
        return {"ok": False, "reason": "no_mdl",
                "message": "no mdl/mdl.json — run `pf bootstrap`"}
    write_connection(d)
    try:
        proc = _wren("dry-plan", "--sql", sql, "--mdl", str(mdl_path(d)),
                     "--connection-file", str(connection_path(d)))
    except FileNotFoundError:
        return {"ok": False, "reason": "not_installed",
                "message": "wren is not on PATH — `uv sync --extra wren`"}
    out = (proc.stdout or "").strip()
    return {"ok": proc.returncode == 0, "sql": out,
            "reason": "" if proc.returncode == 0 else "plan_failed",
            "message": (proc.stderr or out or "")[-1500:]}


def query(project_dir: Path, sql: str, limit: int = 200) -> dict[str, Any]:
    """Answer a question through the semantic layer: Wren plans, we execute.

    Wren's `query` is deliberately not used. Its `duckdb` datasource is a *file
    scanner* — it takes a directory, registers what it finds in a flat namespace,
    and has no concept of the schemas a dbt build actually writes into. Every
    query resolving `main_marts.fct_revenue` came back "schema does not exist"
    while the table was plainly there, because the connector never attached the
    warehouse in the first place.

    The split that works is the honest one: Wren owns semantics — expanding a
    question against the MDL into warehouse SQL, which it does correctly — and
    the warehouse connection stays ours, the same `Warehouse` every other part of
    this platform reads through. It also means a query never travels through a
    second set of credentials.
    """
    d = Path(project_dir)
    if not has_mdl(d):
        return {"ok": False, "reason": "no_mdl", "message": "no mdl/mdl.json"}

    planned = plan(d, sql)
    if not planned["ok"]:
        return planned

    from pf.runtime.warehouse import Warehouse

    wh = Warehouse.for_project(d, d.parents[1].name if len(d.parents) >= 2 else "",
                               d.name)
    statement = planned["sql"]
    try:
        import duckdb

        con = duckdb.connect(str(wh.path), read_only=True)
        try:
            rel = con.sql(statement)
            columns = list(rel.columns)
            rows = [dict(zip(columns, r)) for r in rel.fetchmany(limit)]
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001 — a failed query is a result, not a crash
        return {"ok": False, "reason": "query_failed", "sql": statement,
                "message": f"{type(exc).__name__}: {exc}"[-1500:]}
    return {"ok": True, "rows": rows, "columns": columns, "sql": statement}


def ask(prompt: str) -> dict[str, Any]:
    """Shape a business question into an MDL-aware agent prompt."""
    try:
        proc = _wren("ask", prompt, "--direct", timeout=60)
    except FileNotFoundError:
        return {"ok": False, "message": "wren is not on PATH"}
    return {"ok": proc.returncode == 0,
            "prompt": (proc.stdout or "").strip()[:4000],
            "message": (proc.stderr or "")[-500:]}


# ------------------------------------------------------------------- mdl --
def summarise_mdl(project_dir: Path) -> dict[str, Any]:
    """The semantic layer as the control plane renders it.

    Read straight from the manifest rather than from the graph: this is the
    artefact an external consumer would receive, so showing anything else would
    let the dashboard and the export disagree.
    """
    p = mdl_path(project_dir)
    if not p.exists():
        return {"models": [], "relationships": [], "metrics": [], "views": []}
    try:
        m = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {"models": [], "relationships": [], "metrics": [], "views": []}

    models = []
    for mod in m.get("models") or []:
        cols = mod.get("columns") or []
        models.append({
            "name": mod.get("name", ""),
            "table": (mod.get("tableReference") or {}).get("table", ""),
            "schema": (mod.get("tableReference") or {}).get("schema", ""),
            "columns": len(cols),
            "roles": sorted({(c.get("properties") or {}).get("pf.role", "")
                             for c in cols} - {""}),
            "primary_key": mod.get("primaryKey", ""),
        })
    return {
        "catalog": m.get("catalog", ""), "schema": m.get("schema", ""),
        "data_source": m.get("dataSource", ""),
        "models": sorted(models, key=lambda r: r["name"]),
        "relationships": [
            {"name": r.get("name", ""), "models": r.get("models") or [],
             "join_type": r.get("joinType", "")}
            for r in (m.get("relationships") or [])],
        "metrics": [x.get("name", "") for x in (m.get("metrics") or [])],
        "views": [x.get("name", "") for x in (m.get("views") or [])],
    }


# --------------------------------------------------------------- bootstrap --
def bootstrap_project(root: Path, group: str, project: str,
                      project_dir: Path, config: dict[str, Any]) -> Any:
    from pf.scaffold.bootstrap import StepResult

    if not has_mdl(project_dir):
        # The MDL step runs earlier in the same bootstrap, so this only happens
        # for a project with no dbt project at all.
        return StepResult("wren", "skipped", "no mdl/mdl.json yet")
    write_connection(project_dir, project)
    s = summarise_mdl(project_dir)
    detail = f"{len(s['models'])} model(s), {len(s['relationships'])} relationship(s)"
    if not probe_engine()["ok"]:
        detail += " · engine cannot plan (see `pf tool doctor`)"
    return StepResult("wren", "ok", detail)


# ----------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """An asset check that the emitted MDL is what Wren will actually accept.

    A conformance claim nobody executes is the thing this platform's vendor
    registry exists to prevent, so it is executed: the manifest is re-read and,
    where the engine can plan, a query is planned against it.
    """
    from dagster import AssetKey, MetadataValue, asset

    project_dir = Path(ctx.project_dir)
    prefix = ctx.project.replace("-", "_")
    s = summarise_mdl(project_dir)
    if not s["models"]:
        return ToolContribution()

    deps = [AssetKey([prefix, m["name"]]) for m in s["models"]]

    @asset(
        name="wren_semantic_layer",
        key_prefix=[prefix],
        group_name="semantic",
        deps=deps,
        description="MDL manifest projected for Wren and any other MDL consumer.",
        compute_kind="wren",
        metadata={"dagster/kind": "wren", "tool": "wren"},
    )
    def _wren_mdl(context) -> None:  # noqa: ANN001 — see dagster_runtime note
        summary = summarise_mdl(project_dir)
        probe = probe_engine()
        meta: dict[str, Any] = {
            "models": len(summary["models"]),
            "relationships": len(summary["relationships"]),
            "mdl": MetadataValue.path(str(mdl_path(project_dir))),
            "engine": "ok" if probe["ok"] else f"unusable — {probe['detail']}",
        }
        if probe["ok"] and summary["models"]:
            first = summary["models"][0]["name"]
            r = plan(project_dir, f"select * from {first}")
            meta["plan_check"] = "pass" if r["ok"] else f"fail — {r['message'][:200]}"
        else:
            context.log.warning(
                "Wren engine cannot plan MDL queries here (%s) — the manifest is "
                "still emitted and valid for other consumers.", probe["detail"])
        context.add_output_metadata(meta)

    return ToolContribution(assets=[_wren_mdl])


# ------------------------------------------------------------- capability --
WREN_DOCS = """\
# Wren — semantic layer for {{group}}/{{project}}

`mdl/mdl.json` is this project's semantic layer in MDL, the interchange format a
BI or text-to-SQL layer consumes without being told our internals. It is
generated from the knowledge graph by `pf bootstrap` — never hand-edited.

```bash
pf tool wren mdl {{group}} {{project}}          # what the manifest contains
pf tool wren plan {{group}} {{project}} "<sql>" # expand SQL through the MDL
pf tool wren query {{group}} {{project}} "<sql>"
pf tool doctor {{group}} {{project}}            # is the engine actually usable
```

## There is no Wren web UI

Upstream's Docker chat-first BI app is `legacy/v1` ("Wren GenBI Classic"). Current
WrenAI is a CLI plus `wren serve`, which serves **MCP**, not a web page. The
semantic surface you look at is `pf ui` -> **Semantics**, which reads this same
manifest. Nothing is being iframed, because there is nothing to iframe.

## Against the review

`pf ui` -> **Workspace** joins this manifest to Recce's recorded diff on the
model behind each entity, so "fct_revenue moved" is read as which semantic
entity changed and which ontology roles ride on it. It needs the `recce` tool on
as well; both are on by default for a new group.
"""

CAPABILITY = Capability(
    name="wren",
    description="MDL semantic layer: project it, inspect it, query through it.",
    files={"docs/wren.md": WREN_DOCS},
    settings={"permissions": {"allow": ["Bash(pf tool wren:*)", "Bash(wren:*)"]}},
    gate={
        # Generated from the graph. Editing it forks the semantic layer from the
        # models it claims to describe.
        "denylist": ["**/mdl/mdl.json", "**/mdl/connection.json"],
    },
)


TOOL = Tool(
    name="wren",
    title="Wren",
    summary="MDL semantic layer — project it, inspect it, query through it.",
    url="https://github.com/Canner/WrenAI",
    scope=frozenset({"project", "group"}),
    capability=CAPABILITY,
    default_enabled=True,
    requires=(
        Requirement("python", "wren", "uv sync --extra wren"),
        Requirement("binary", "wren", "uv sync --extra wren"),
    ),
    dbt=DbtBinding(needs_manifest=True, artefacts=(MDL_REL, CONNECTION_REL)),
    # No Surface, deliberately: upstream ships no web UI any more. See the module
    # docstring. The control plane renders the manifest itself.
    surface=None,
    health="pf.tools.wren:probe_engine",
    bootstrap="pf.tools.wren:bootstrap_project",
    dagster="pf.tools.wren:dagster_assets",
    commands="pf.tools.wren:register_commands",
    stack_layer={
        "layer": "semantics", "title": "Semantic layer (Wren MDL)",
        "upstream": "wrenai", "toolkits": [],
        "artefacts": "mdl/mdl.json", "node_kinds": ["Metric", "Dimension"],
    },
)


# -------------------------------------------------------------------- cli --
def register_commands(app: Any) -> None:
    import typer
    from rich.console import Console
    from rich.table import Table

    console = Console()
    wren_app = typer.Typer(help="Wren: the MDL semantic layer.")

    def _pdir(group: str, project: str) -> Path:
        from pf.cli import pdir
        return pdir(group, project)

    @wren_app.command("mdl")
    def cmd_mdl(group: str, project: str) -> None:
        """What the emitted manifest contains."""
        s = summarise_mdl(_pdir(group, project))
        if not s["models"]:
            console.print("[yellow]no MDL yet — run `pf bootstrap`[/]")
            raise typer.Exit(1)
        t = Table("model", "relation", "cols", "roles",
                  title=f"MDL · {s.get('catalog')}.{s.get('schema')} "
                        f"({s.get('data_source')})")
        for m in s["models"]:
            t.add_row(m["name"], f"{m['schema']}.{m['table']}",
                      str(m["columns"]), ", ".join(m["roles"]) or "—")
        console.print(t)
        console.print(f"  [dim]{len(s['relationships'])} relationship(s)[/]")

    @wren_app.command("plan")
    def cmd_plan(group: str, project: str, sql: str) -> None:
        """Expand SQL through the MDL. No warehouse access."""
        r = plan(_pdir(group, project), sql)
        if r["ok"]:
            console.print(r["sql"])
            raise typer.Exit(0)
        console.print(f"[red]{r.get('reason')}[/] {r.get('message','')}")
        raise typer.Exit(1)

    @wren_app.command("query")
    def cmd_query(group: str, project: str, sql: str,
                  limit: int = typer.Option(50)) -> None:
        """Execute SQL through the semantic layer."""
        r = query(_pdir(group, project), sql, limit=limit)
        if not r["ok"]:
            console.print(f"[red]{r.get('reason')}[/] {r.get('message','')}")
            raise typer.Exit(1)
        rows = r.get("rows") or []
        if not rows:
            console.print("[dim]no rows[/]")
            raise typer.Exit(0)
        cols = list(rows[0].keys())
        t = Table(*cols)
        for row in rows[:limit]:
            t.add_row(*[str(row.get(c, "")) for c in cols])
        console.print(t)

    @wren_app.command("doctor")
    def cmd_doctor() -> None:
        """Can this install actually plan an MDL query?"""
        p = probe_engine()
        mark = "[green]✓[/]" if p["ok"] else "[red]✗[/]"
        console.print(f"{mark} wren engine — {p['detail']}")
        if not p["ok"]:
            console.print("[dim]Probed with a minimal hand-written MDL, so this is "
                          "the install rather than this project's manifest.[/]")
        raise typer.Exit(0 if p["ok"] else 1)

    app.add_typer(wren_app, name="wren")
