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

## What is around the planner

`pf.tools.wren_context` writes the workspace Wren's CLI wants — one per
project, holding the manifest an LLM may read (restricted columns withheld), the
rules it is handed and the questions it has answered before — and
`pf.tools.wren_gate` is the road every question takes through it: policy, plan,
dry-run, execute, ledger. This module is the tool: what it declares, what it
bootstraps, what it contributes to Dagster, and the `pf tool wren` commands.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pf.capabilities import Capability
from pf.features import Feature
from pf.tools import wren_context as wc
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


def _scope(project_dir: Path) -> tuple[Path, str, str]:
    """(repo root, group, project) from where a project directory sits."""
    from pf import obs

    d = Path(project_dir)
    return obs.repo_root(d), (d.parents[1].name if len(d.parents) >= 2 else ""), d.name


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
    if path.exists() and path.read_text(encoding="utf-8") == body:
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
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
            m.write_text(json.dumps(PROBE_MDL), encoding="utf-8")
            c.write_text(json.dumps({"datasource": "duckdb"}), encoding="utf-8")
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
    """Expand SQL through the MDL without touching the warehouse.

    Against the workspace's LLM-facing manifest where the workspace exists — a
    column withheld from it has no name the planner knows — and the full
    manifest only where no workspace was ever written.
    """
    d = Path(project_dir)
    if not has_mdl(d):
        return {"ok": False, "reason": "no_mdl",
                "message": "no mdl/mdl.json — run `pf bootstrap`"}
    write_connection(d)
    manifest = _llm_target(d)
    try:
        if wc.exists(d):
            proc = wc.run(wc.workspace(d), "dry-plan", "--sql", sql, "--mdl", str(manifest),
                          "--connection-file", str(connection_path(d)))
        else:
            proc = _wren("dry-plan", "--sql", sql, "--mdl", str(manifest),
                         "--connection-file", str(connection_path(d)))
    except FileNotFoundError:
        return {"ok": False, "reason": "not_installed",
                "message": "wren is not on PATH — `uv sync --extra wren`"}
    out = (proc.stdout or "").strip()
    return {"ok": proc.returncode == 0, "sql": out,
            "reason": "" if proc.returncode == 0 else "plan_failed",
            "message": (proc.stderr or out or "")[-1500:]}


def _llm_target(d: Path) -> Path:
    """The manifest an agent's question is planned against: the workspace's
    LLM-facing target (regenerated when absent), or the full manifest where no
    workspace was ever written."""
    if wc.exists(d):
        if not wc.target_path(d).is_file():
            root, g, p = _scope(d)
            wc.refresh(root, g, p, d, hide_roles=wc.hide_roles_for(root, g, p))
        return wc.target_path(d)
    return mdl_path(d)


def translate_cube(project_dir: Path, cube: str, measures: list[str], dimensions: list[str] | None = None,
                   time_dimension: str = "", filters: list[str] | None = None,
                   limit: int | None = None) -> dict[str, Any]:
    """A cube question — measures by dimensions, a time grain, filters — as one
    MDL-level SELECT, without running it. The engine writes the GROUP BY and the
    measure expressions, so a ratio is re-divided and a price never summed."""
    d = Path(project_dir)
    if not has_mdl(d):
        return {"ok": False, "reason": "no_mdl", "message": "no mdl/mdl.json — run `pf bootstrap`"}
    write_connection(d)
    target = _llm_target(d)
    try:
        ok, out = wc.cube_sql(wc.workspace(d) if wc.exists(d) else d, target, connection_path(d), cube,
                              measures, dimensions, time_dimension, filters, limit)
    except FileNotFoundError:
        return {"ok": False, "reason": "not_installed", "message": "wren is not on PATH — `uv sync --extra wren`"}
    return {"ok": ok, "sql": out if ok else "", "reason": "" if ok else "translate_failed",
            "message": "" if ok else out}


def cube(project_dir: Path, cube_name: str, measures: list[str], dimensions: list[str] | None = None,
         time_dimension: str = "", filters: list[str] | None = None, limit: int = 200) -> dict[str, Any]:
    """A cube question on the gated road: translate → policy → plan → dry-run →
    execute → ledger. The same outcome shape as `query`."""
    from pf.tools import wren_gate

    d = Path(project_dir)
    root, group, project = _scope(d)
    out = wren_gate.ask_cube(d, group, project, cube_name, measures, dimensions or [], time_dimension,
                             filters or [], limit=limit, root=root)
    return {"ok": out.ok, "rows": out.rows, "columns": out.columns, "sql": out.planned_sql,
            "stage": out.stage, "reason": "" if out.ok else f"{out.stage}_failed",
            "message": out.message, "run_id": out.run_id, "attempt": out.attempt}


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

    The road from SQL to rows is `pf.tools.wren_gate.ask`: policy, plan,
    dry-run, execute, and a ledger entry whichever way it went.
    """
    from pf.tools import wren_gate

    d = Path(project_dir)
    root, group, project = _scope(d)
    out = wren_gate.ask(d, group, project, sql, limit=limit, root=root)
    return {"ok": out.ok, "rows": out.rows, "columns": out.columns, "sql": out.planned_sql,
            "stage": out.stage, "reason": "" if out.ok else f"{out.stage}_failed",
            "message": out.message, "run_id": out.run_id, "attempt": out.attempt}


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
        m = json.loads(p.read_text(encoding="utf-8"))
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
    hide = tuple(str(r) for r in (config.get("hide_roles") or ())) if isinstance(config, dict) else ()
    _, b = wc.refresh(root, group, project, project_dir, hide_roles=hide)
    s = summarise_mdl(project_dir)
    withheld = sum(len(v) for v in b.hidden.values())
    detail = (f"{len(s['models'])} model(s), {len(s['relationships'])} relationship(s); "
              f"workspace: {len(b.tracked) - 1} rule file(s), {withheld} column(s) withheld")
    if not probe_engine()["ok"]:
        detail += " · engine cannot plan (see `pf tool doctor`)"
    return StepResult("wren", "ok", detail)


# ----------------------------------------------------------------- dagster --
def dagster_assets(ctx: ToolContext) -> ToolContribution:
    """An asset that the emitted MDL is what Wren will actually accept.

    A conformance claim nobody executes is the thing this platform's vendor
    registry exists to prevent, so it is executed: the manifest is re-read and,
    where the engine can plan, a query is planned against it and the whole
    workspace — every model, every cube — is checked against the warehouse the
    run just built (`pf.tools.wren_context.check`).
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
            if r["ok"]:
                # The planned SQL compiles against the warehouse the models were
                # built into — the same dry-run every question goes through.
                from pf.runtime.warehouse import Warehouse
                from pf.tools import wren_gate

                wh = Warehouse.for_project(project_dir, getattr(ctx, "group", ""), ctx.project)
                if Path(wh.path).is_file():
                    err = wren_gate.dry_run(Path(wh.path), r["sql"])
                    meta["dry_run"] = "pass" if err is None else f"fail — {err[:200]}"
            if wc.exists(project_dir):
                # After a build, the whole workspace: every model and every cube
                # planned, each cube bound on the warehouse just written. A
                # measure that reads a column its base lost fails here, on the
                # run that lost it, not on the next question someone asks.
                from pf import obs

                root = obs.repo_root(project_dir)
                problems = wc.check(root, getattr(ctx, "group", ""), ctx.project, project_dir, plan=True)
                meta["cubes"] = len(json.loads(mdl_path(project_dir).read_text(encoding="utf-8")).get("cubes") or [])
                meta["workspace_check"] = "pass" if not problems else MetadataValue.md(
                    "\n".join(f"- {x}" for x in problems[:20]))
                for x in problems:
                    context.log.warning("wren workspace: %s", x)
        else:
            context.log.warning(
                "Wren engine cannot plan MDL queries here (%s) — the manifest is "
                "still emitted and valid for other consumers.", probe["detail"])
        context.add_output_metadata(meta)

    return ToolContribution(assets=[_wren_mdl])


# ------------------------------------------------------------- capability --
WREN_DOCS = """\
# Wren — conversational analytics for {{group}}/{{project}}

`mdl/mdl.json` is this project's semantic layer in MDL, generated from the
knowledge graph by `pf bootstrap` — never hand-edited. Beside it, `mdl/wren/` is
the workspace Wren's CLI reads, generated from the same inputs:

| Path | What | Tracked |
|---|---|---|
| `mdl/wren/wren_project.yml` | name, catalog, schema, data source | yes |
| `mdl/wren/target/mdl.json` | the manifest an LLM may see: PII and `hide_roles` columns withheld | no |
| `mdl/wren/knowledge/rules/NN-*.md` | scope, concepts and roles, metrics and cubes, policies, enumerations | yes |
| `mdl/wren/knowledge/sql/*.md` | questions answered before, as `wren memory store` writes them | yes |
| `mdl/wren/.wren/memory/` | the derived index (`wren[memory]`, LanceDB) | no |

Every `wren` call this project makes runs inside that workspace with
`WREN_PROJECT_HOME` and `WREN_HOME` pointed at it. Nothing is read from
`~/.wren`, and nothing of another project is visible.

```bash
pf tool wren workspace {{group}} {{project}}       # (re)generate the workspace; --index for memory
pf tool wren check {{group}} {{project}}           # is the committed workspace what the manifest projects?
pf tool wren context {{group}} {{project}} "<q>"   # rules + remembered questions + schema, for one question
pf tool wren plan {{group}} {{project}} "<sql>"    # expand SQL through the MDL, no warehouse
pf tool wren query {{group}} {{project}} "<sql>"   # policy → plan → dry-run → execute → ledger
pf tool wren cube {{group}} {{project}} --cube <c> --measures <m> --dimensions <d>   # a cube question, same road
pf tool wren store {{group}} {{project}} --nl "<q>" --sql "<sql>"   # remember a validated answer
pf tool doctor {{group}} {{project}}               # is the engine actually usable
```

## The road every question takes

`pf tool wren query` and `pf tool wren cube` (the `wren_query` and `wren_cube`
MCP tools) never run what they are given. A cube question is first translated
into one `SELECT` by the engine. The gate checks the statement is one read-only
`SELECT`, plans it through the
LLM-facing manifest, `EXPLAIN`s the plan on this project's warehouse read-only,
executes it row-limited, and appends the outcome — refused or not — to
`groups/{{group}}/loop-ledger.json` as a `wren-query` run. A statement refused
three times is refused with "escalate". `loop-constraints.md` applies.

## MCP

`.mcp.json` registers `wren serve mcp --project mdl/wren --no-connect`: Wren's
own context tools (models, cubes, `dry_plan`) over this workspace, in
transpile-only mode. Execution goes through `pf`'s `wren_query`, which is the
gated road above — never through a second connection.

## There is no Wren web UI

Upstream's Docker chat-first BI app is `legacy/v1` ("Wren GenBI Classic"). Current
WrenAI is a CLI plus `wren serve`, which serves **MCP**, not a web page. The
semantic surface you look at is `pf ui` -> **Semantics**, which reads the same
manifest. Nothing is being iframed, because there is nothing to iframe.
"""

CAPABILITY = Capability(
    name="wren",
    description="MDL semantic layer: project it, inspect it, ask questions through it — gated and recorded.",
    files={"docs/wren.md": WREN_DOCS},
    settings={"permissions": {"allow": ["Bash(pf tool wren:*)", "Bash(wren:*)"]}},
    # Wren's own context tools over this project's workspace, transpile-only:
    # `--no-connect` removes run_sql, dry_run and query_cube, so the only way to
    # rows is `pf`'s gated `wren_query`. `--no-sync` keeps an MCP launch from
    # touching the environment.
    mcp={"wren": {"command": "uv",
                  "args": ["run", "--no-sync", "wren", "serve", "mcp", "--project", "mdl/wren",
                           "--no-connect", "--quiet"]}},
    gate={
        # Generated from the graph. Editing any of it forks the semantic layer
        # from the models it claims to describe; the derived index and the
        # LLM-facing manifest are rebuilt, never edited.
        "denylist": ["**/mdl/mdl.json", "**/mdl/connection.json", "**/mdl/wren/wren_project.yml",
                     "**/mdl/wren/target/**", "**/mdl/wren/.wren/**"],
    },
)

TOOL = Tool(
    name="wren",
    title="Wren",
    summary="MDL semantic layer — project it, inspect it, ask questions through it.",
    url="https://github.com/Canner/WrenAI",
    scope=frozenset({"project", "group"}),
    capability=CAPABILITY,
    default_enabled=True,
    requires=(
        Requirement("python", "wren", "uv sync --extra wren"),
        Requirement("binary", "wren", "uv sync --extra wren"),
    ),
    dbt=DbtBinding(needs_manifest=True, artefacts=(MDL_REL, CONNECTION_REL)),
    # The workspace is a directory of its own under `mdl/`, so the architecture
    # map names it rather than folding it into the manifest's row.
    features=(
        Feature(
            "wren_workspace",
            "Wren workspace",
            "semantics",
            "the semantic layer as an LLM may read it: restricted columns withheld, "
            "rules and remembered questions beside it",
            ("mdl/wren/**",),
            optional=True,
            made_by="pf tool wren workspace",
        ),
    ),
    # No Surface, deliberately: upstream ships no web UI any more. See the module
    # docstring. The control plane renders the manifest itself.
    surface=None,
    health="pf.tools.wren:probe_engine",
    bootstrap="pf.tools.wren:bootstrap_project",
    dagster="pf.tools.wren:dagster_assets",
    commands="pf.tools.wren:register_commands",
    stack_layer={
        "layer": "semantics", "title": "Semantic layer (Wren MDL)",
        "upstream": "wrenai", "toolkits": ["wren-analytics"],
        "artefacts": "mdl/mdl.json, mdl/wren/**", "node_kinds": ["Metric", "Dimension"],
    },
)


# -------------------------------------------------------------------- cli --
def _print_outcome(r: dict[str, Any], limit: int) -> None:
    import typer
    from rich.console import Console
    from rich.table import Table

    console = Console()
    if not r["ok"]:
        run = f"run {r['run_id']}, attempt {r['attempt']}"
        console.print(f"[red]✗ {r['stage']}[/] {r['message']}  [dim]({run})[/]")
        raise typer.Exit(1)
    rows = r.get("rows") or []
    if not rows:
        console.print(f"[dim]no rows[/]  [dim](run {r['run_id']})[/]")
        raise typer.Exit(0)
    cols = r.get("columns") or list(rows[0].keys())
    t = Table(*cols)
    for row in rows[:limit]:
        t.add_row(*[str(row.get(c, "")) for c in cols])
    console.print(t)
    console.print(f"[dim]{len(rows)} row(s) · run {r['run_id']}[/]")


def register_commands(app: Any) -> None:
    import typer
    from rich.console import Console
    from rich.table import Table

    console = Console()
    wren_app = typer.Typer(help="Wren: the MDL semantic layer, and the gated road through it.")

    def _pdir(group: str, project: str) -> Path:
        from pf.cli import pdir
        return pdir(group, project)

    def _targets(group: str, project: str, all_: bool) -> list[tuple[str, str, Path]]:
        from pf.cli import all_projects

        if all_:
            return list(all_projects())
        if not (group and project):
            console.print("[red]give a group and project, or --all[/]")
            raise typer.Exit(1)
        return [(group, project, _pdir(group, project))]

    def _root() -> Path:
        from pf.cli import root
        return root()

    def _fail(r: dict[str, Any]) -> None:
        console.print(f"[red]{r.get('reason') or r.get('stage')}[/] {r.get('message', '')}")
        raise typer.Exit(1)

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

    @wren_app.command("workspace")
    def cmd_workspace(
        group: str = typer.Argument(""),
        project: str = typer.Argument(""),
        all_: bool = typer.Option(False, "--all", help="every project"),
        index: bool = typer.Option(False, "--index", help="also (re)build the memory index"),
    ) -> None:
        """(Re)generate `mdl/wren/` from the manifest, the ontology and the graph."""
        root = _root()
        for g, p, d in _targets(group, project, all_):
            if not has_mdl(d):
                console.print(f"[yellow]{g}/{p}: no mdl/mdl.json — run `pf semantic mdl {g} {p}`[/]")
                continue
            changed, b = wc.refresh(root, g, p, d, hide_roles=wc.hide_roles_for(root, g, p))
            withheld = sum(len(v) for v in b.hidden.values())
            console.print(f"[green]✓[/] {g}/{p}: {len(b.tracked) - 1} rule file(s), {withheld} column(s) withheld, "
                          f"{len(changed)} file(s) changed")
            if index:
                proc = wc.index(d)
                tail = (proc.stdout or proc.stderr or "").strip().splitlines()
                console.print(f"  [dim]{tail[-1] if tail else 'indexed'}[/]")

    @wren_app.command("check")
    def cmd_check(
        group: str = typer.Argument(""),
        project: str = typer.Argument(""),
        all_: bool = typer.Option(False, "--all", help="every project"),
        no_plan: bool = typer.Option(False, "--no-plan", help="skip the planner canary even if the engine is present"),
    ) -> None:
        """Is every committed workspace what its manifest projects? Exits 1 otherwise."""
        root = _root()
        problems: list[str] = []
        for g, p, d in _targets(group, project, all_):
            problems += wc.check(root, g, p, d, plan=not no_plan)
        for x in problems:
            console.print(f"[red]✗[/] {x}")
        if problems:
            console.print("[dim]run `pf tool wren workspace --all` and commit mdl/wren/[/]")
            raise typer.Exit(1)
        console.print("[green]✓[/] every Wren workspace matches its semantic layer")

    @wren_app.command("context")
    def cmd_context(group: str, project: str, question: str,
                    limit: int = typer.Option(3, help="remembered questions to recall")) -> None:
        """What to read before planning one question: rules, remembered answers, schema."""
        d = _pdir(group, project)
        if not wc.exists(d):
            console.print(f"[yellow]no workspace — run `pf tool wren workspace {group} {project}`[/]")
            raise typer.Exit(1)
        ctx = wc.context(d, question, limit)
        console.print(ctx["rules"].rstrip())
        console.print("\n[bold]Answered before[/]")
        for pair in ctx["pairs"]:
            console.print(f"- {pair.get('nl_query')}\n    {pair.get('sql_query')}")
        if not ctx["pairs"]:
            console.print("- none that resemble this")
        if ctx["schema"]:
            console.print("\n[bold]Schema[/]\n" + ctx["schema"].rstrip())

    @wren_app.command("rules")
    def cmd_rules(group: str, project: str) -> None:
        """The rules an LLM is handed for this project."""
        console.print(wc.instructions(_pdir(group, project)).rstrip())

    @wren_app.command("recall")
    def cmd_recall(group: str, project: str, question: str,
                   limit: int = typer.Option(3)) -> None:
        """Questions answered before that resemble this one."""
        for pair in wc.recall(_pdir(group, project), question, limit):
            console.print(f"- {pair.get('nl_query')}\n    {pair.get('sql_query')}")

    @wren_app.command("store")
    def cmd_store(group: str, project: str,
                  nl: str = typer.Option(..., "--nl", help="the question, in the asker's words"),
                  sql: str = typer.Option(..., "--sql", help="the SQL that answered it, as planned by the gate"),
                  tags: str = typer.Option("", help="comma-separated")) -> None:
        """Remember a validated answer as `knowledge/sql/<slug>.md` — a tracked file, reviewed like code."""
        d = _pdir(group, project)
        reason = __import__("pf.tools.wren_gate", fromlist=["policy"]).policy(sql)
        if reason:
            console.print(f"[red]not stored — {reason}[/]")
            raise typer.Exit(1)
        proc = wc.store(d, nl, sql, tags)
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        console.print(tail[-1] if tail else "stored")
        raise typer.Exit(proc.returncode)

    @wren_app.command("index")
    def cmd_index(group: str, project: str) -> None:
        """(Re)build the memory index from the workspace. A no-op on the grep backend."""
        proc = wc.index(_pdir(group, project))
        console.print((proc.stdout or proc.stderr or "").strip())
        raise typer.Exit(proc.returncode)

    @wren_app.command("plan")
    def cmd_plan(group: str, project: str, sql: str) -> None:
        """Expand SQL through the MDL. No warehouse access."""
        r = plan(_pdir(group, project), sql)
        if r["ok"]:
            console.print(r["sql"])
            raise typer.Exit(0)
        _fail(r)

    @wren_app.command("query")
    def cmd_query(group: str, project: str, sql: str,
                  limit: int = typer.Option(50)) -> None:
        """Policy → plan → dry-run → execute → ledger. Read-only, row-limited, recorded."""
        _print_outcome(query(_pdir(group, project), sql, limit=limit), limit)

    @wren_app.command("cube")
    def cmd_cube(group: str, project: str,
                 cube_name: str = typer.Option(..., "--cube", "-c", help="cube name, as `pf tool wren rules` lists it"),
                 measures: str = typer.Option(..., help="comma-separated measure names"),
                 dimensions: str = typer.Option("", help="comma-separated dimension names"),
                 time_dimension: str = typer.Option("", help="name:granularity[:start,end], e.g. trade_date:month"),
                 filters: list[str] = typer.Option(
                     [], "--filter", help="dim:op[:value], repeatable; op is eq, neq, in, not_in, gt, gte, "
                     "lt, lte, contains, starts_with, is_null, is_not_null"),
                 limit: int = typer.Option(50),
                 sql_only: bool = typer.Option(False, "--sql-only",
                                               help="print the translated SQL; run nothing")) -> None:
        """A measure-by-dimension question on the gated road: translate → policy →
        plan → dry-run → execute → ledger. Read-only, row-limited, recorded."""
        ms = [m.strip() for m in measures.split(",") if m.strip()]
        ds = [x.strip() for x in dimensions.split(",") if x.strip()]
        if sql_only:
            r = translate_cube(_pdir(group, project), cube_name, ms, ds, time_dimension, filters, limit)
            if not r["ok"]:
                _fail(r)
            console.print(r["sql"])
            raise typer.Exit(0)
        r = cube(_pdir(group, project), cube_name, ms, ds, time_dimension, filters, limit=limit)
        _print_outcome(r, limit)

    @wren_app.command("serve")
    def cmd_serve(group: str, project: str,
                  connect: bool = typer.Option(False, "--connect",
                                               help="also expose run_sql (never for an agent)")) -> None:
        """Wren's MCP server over this project's workspace, transpile-only by default."""
        import os
        import sys

        d = _pdir(group, project)
        if not wc.exists(d):
            console.print(f"[yellow]no workspace — run `pf tool wren workspace {group} {project}`[/]")
            raise typer.Exit(1)
        ws = wc.workspace(d)
        args = ["wren", "serve", "mcp", "--project", str(ws), "--quiet"] + ([] if connect else ["--no-connect"])
        os.environ.update(wc.env_for(ws))
        os.chdir(ws)
        os.execvp(args[0], args)  # noqa: S606 — replaces this process with the server, on purpose
        sys.exit(1)

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
