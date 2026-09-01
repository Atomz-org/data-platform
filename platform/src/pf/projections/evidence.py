"""Project the semantic layer into an Evidence BI project.

This is the last link in the chain the rest of the platform builds toward:

    ontology -> topology -> dbt marts -> MetricFlow metrics -> MDL -> Evidence

Nothing here invents a number. Every value on every generated page traces to a
MetricFlow metric compiled into `queries/metrics/<name>.sql`. That is the same
contract Atomz-org/Evidence-BI states as its first principle — *pages never
restate business logic; if a dashboard needs a number that does not exist, the
fix is a metric PR* — and it is the reporting-layer expression of this platform's
own routing rule (metrics before ad-hoc SQL).

Two correctness rules are enforced in the generated SQL rather than left to the
page author:

  * **Ratio metrics carry their numerator and denominator.** A page re-divides at
    its own display grain. `avg(average_order_value)` is wrong at every grain
    except the one it was computed at, and it is the single most common BI bug.
  * **A metric's filter lives in the metric**, not in the page. Two pages filtering
    differently is how one company ends up with two revenues.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Validated categorical palette (CVD ΔE >= 8 adjacent, normal-vision ΔE >= 15,
# light and dark stepped separately). Do not hand-edit: these values come from a
# run of the palette validator, and re-picking them by eye is how a chart becomes
# unreadable for ~8% of readers.
PALETTE_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PALETTE_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}


@dataclass
class MetricSpec:
    name: str
    label: str
    kind: str  # simple | ratio | derived | cumulative
    model: str  # physical table the measure sits on
    expression: str  # aggregate expression
    filter_sql: str = ""
    time_column: str = ""
    dimensions: list[str] = None  # categorical dimensions available
    numerator: str = ""
    denominator: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        self.dimensions = self.dimensions or []


# --------------------------------------------------------------- reading ----
def _load(project_dir: Path) -> tuple[dict, dict]:
    target = project_dir / "transform" / "target"
    sm = target / "semantic_manifest.json"
    mdl = project_dir / "mdl" / "mdl.json"
    return (json.loads(sm.read_text()) if sm.exists() else {}, json.loads(mdl.read_text()) if mdl.exists() else {})


_DIM_REF = re.compile(r"\{\{\s*Dimension\(\s*'([^']+)'\s*\)\s*\}\}")


def _translate_filter(f: str) -> str:
    """MetricFlow filter -> plain SQL.

    `{{ Dimension('payment__payment_status') }} = 'succeeded'` becomes
    `payment_status = 'succeeded'`: the entity prefix is MetricFlow's namespace,
    not a column name.
    """
    if not f:
        return ""
    return _DIM_REF.sub(lambda m: m.group(1).split("__")[-1], f).strip()


def collect_metrics(project_dir: Path) -> list[MetricSpec]:
    sm, _ = _load(project_dir)
    if not sm:
        return []

    measures: dict[str, dict[str, Any]] = {}
    for model in sm.get("semantic_models") or []:
        table = (model.get("node_relation") or {}).get("alias") or model.get("name")
        time_col = (model.get("defaults") or {}).get("agg_time_dimension") or ""
        dims = [d["name"] for d in (model.get("dimensions") or []) if d.get("type") != "time"]
        for m in model.get("measures") or []:
            measures[m["name"]] = {
                "expr": f"{m.get('agg', 'sum')}({m.get('expr') or m['name']})",
                "model": table,
                "time": time_col,
                "dims": dims,
            }

    specs: list[MetricSpec] = []
    by_name: dict[str, MetricSpec] = {}
    for m in sm.get("metrics") or []:
        tp = m.get("type_params") or {}
        kind = (m.get("type") or "simple").lower()
        flt = _translate_filter(_filter_text(m.get("filter")))

        if kind == "simple":
            measure = _measure_name(tp.get("measure"))
            src = measures.get(measure)
            if not src:
                continue
            spec = MetricSpec(
                name=m["name"],
                label=m.get("label") or m["name"],
                kind="simple",
                model=src["model"],
                expression=src["expr"],
                filter_sql=flt,
                time_column=src["time"],
                dimensions=src["dims"],
                description=m.get("description", ""),
            )
        elif kind == "ratio":
            num = by_name.get(_metric_name(tp.get("numerator")))
            den = by_name.get(_metric_name(tp.get("denominator")))
            if not num or not den:
                continue
            spec = MetricSpec(
                name=m["name"],
                label=m.get("label") or m["name"],
                kind="ratio",
                model=num.model,
                expression=f"{num.expression} / nullif({den.expression}, 0)",
                filter_sql=num.filter_sql,
                time_column=num.time_column,
                dimensions=num.dimensions,
                numerator=num.name,
                denominator=den.name,
                description=m.get("description", ""),
            )
        else:
            base = next(
                (by_name[_metric_name(x)] for x in (tp.get("metrics") or []) if _metric_name(x) in by_name), None
            )
            if not base:
                continue
            spec = MetricSpec(
                name=m["name"],
                label=m.get("label") or m["name"],
                kind=kind,
                model=base.model,
                expression=base.expression,
                filter_sql=base.filter_sql,
                time_column=base.time_column,
                dimensions=base.dimensions,
                description=m.get("description", ""),
            )
        specs.append(spec)
        by_name[spec.name] = spec
    return specs


def _filter_text(f: Any) -> str:
    if isinstance(f, str):
        return f
    if isinstance(f, dict):
        parts = f.get("where_filters") or []
        return " and ".join(p.get("where_sql_template", "") for p in parts)
    return ""


def _measure_name(v: Any) -> str:
    return v.get("name") if isinstance(v, dict) else (v or "")


def _metric_name(v: Any) -> str:
    return v.get("name") if isinstance(v, dict) else (v or "")


# --------------------------------------------------------------- writing ----
def _metric_sql(spec: MetricSpec, schema: str) -> str:
    where = f"\nwhere {spec.filter_sql}" if spec.filter_sql else ""
    dims = list(spec.dimensions)[:3]
    dim_sql = "".join(f",\n    {d}" for d in dims)
    group_by = ", ".join(str(i + 1) for i in range(1 + len(dims)))

    head = [
        f"-- metric: {spec.name} ({spec.kind}) — generated by `pf report build`",
        f"-- {spec.description or spec.label}",
        "-- Do not edit. Change the metric in transform/models/semantic/, then rerun.",
    ]
    if spec.kind == "ratio":
        head += [
            "-- Ratio rule: re-divide at the display grain —",
            f"--   sum({spec.numerator}) / sum({spec.denominator})",
            f"-- NEVER avg({spec.name}). Components are carried for exactly that.",
        ]

    body = ["select", f"    {spec.time_column} as metric_time{dim_sql},"]
    if spec.kind == "ratio":
        body.append(f"    {_num_expr(spec)} as {spec.numerator},")
        body.append(f"    {_den_expr(spec)} as {spec.denominator},")
    body.append(f"    {spec.expression} as {spec.name}")
    body.append(f"from {schema}.{spec.model}{where}")
    body.append(f"group by {group_by}")
    body.append("order by 1")
    return "\n".join(head + body) + "\n"


def _num_expr(spec: MetricSpec) -> str:
    return spec.expression.split(" / nullif(")[0]


def _den_expr(spec: MetricSpec) -> str:
    tail = spec.expression.split(" / nullif(")
    return tail[1].rsplit(", 0)", 1)[0] if len(tail) > 1 else "1"


def _index_page(project: str, specs: list[MetricSpec]) -> str:
    """Standard page anatomy: title + context -> filter row -> KPI row ->
    primary trend -> breakdown -> detail. Never a wall of charts."""
    simple = [s for s in specs if s.kind in ("simple", "ratio")]
    kpis = simple[:4]
    trend = next((s for s in specs if s.kind == "simple"), None)
    dim = next((d for s in specs for d in s.dimensions), None)

    q = "\n".join(f"  - metrics/{s.name}.sql" for s in specs)
    lines = [
        "---",
        f"title: {project} — Overview",
        "queries:",
        q,
        "---",
        "",
        "Every number on this page is a governed metric compiled from the dbt",
        "semantic layer into `queries/metrics/`. Nothing here restates business",
        "logic — if a figure you need is missing, the fix is a metric definition,",
        "not SQL in this page.",
        "",
    ]

    if trend:
        lines += [
            "```sql date_bounds",
            "-- DateRange reads min()/max() from ONE column, so both bounds must",
            "-- arrive as two rows in that column — not two columns of one row.",
            f"select min(metric_time) as metric_time from ${{metrics_{trend.name}}}",
            "union all",
            f"select max(metric_time) from ${{metrics_{trend.name}}}",
            "```",
            "",
            "<DateRange name=period data={date_bounds} dates=metric_time/>",
            "",
        ]

    # SQL fences must sit at the top level. Inside a component block such as
    # <Grid>, Evidence hoists the query into a scope where its QueryViewer is not
    # imported, and the build fails with "'QueryViewer' is not defined" — an error
    # that names neither the page nor the block that caused it.
    for s in kpis:
        lines += [
            f"```sql kpi_{s.name}",
            (
                f"select sum({s.numerator}) / nullif(sum({s.denominator}), 0) as {s.name}"
                if s.kind == "ratio"
                else f"select sum({s.name}) as {s.name}"
            ),
            f"from ${{metrics_{s.name}}}",
            "```",
            "",
        ]

    if kpis:
        lines += ["<Grid cols=" + str(min(len(kpis), 4)) + ">", ""]
        for s in kpis:
            fmt = "usd0" if _is_money(s) else "num0"
            lines.append(f"<BigValue data={{kpi_{s.name}}} value={s.name} title='{s.label}' fmt={fmt}/>")
        lines += ["", "</Grid>", ""]

    if trend:
        lines += [
            f"## {trend.label} over time",
            "",
            "```sql trend",
            f"select metric_time, sum({trend.name}) as {trend.name}",
            f"from ${{metrics_{trend.name}}}",
            "group by 1 order by 1",
            "```",
            (f"<LineChart data={{trend}} x=metric_time y={trend.name} yFmt={'usd0' if _is_money(trend) else 'num0'}/>"),
            "",
        ]

    if trend and dim:
        lines += [
            f"## {trend.label} by {dim.replace('_', ' ')}",
            "",
            "```sql breakdown",
            f"select {dim}, sum({trend.name}) as {trend.name}",
            f"from ${{metrics_{trend.name}}}",
            f"where {dim} is not null",
            "group by 1 order by 2 desc",
            "```",
            (
                f"<BarChart data={{breakdown}} x={dim} y={trend.name} swapXY=true "
                f"xFmt={'usd0' if _is_money(trend) else 'num0'}/>"
            ),
            "",
            "## Detail",
            "",
            "<DataTable data={breakdown} rows=15/>",
            "",
        ]

    lines += [
        "---",
        "",
        "_Generated by `pf report build`. Metric definitions live in",
        "`transform/models/semantic/`; this page is a projection of them._",
    ]
    return "\n".join(_fence_spacing(lines)) + "\n"


def _metric_page(project: str, spec: MetricSpec) -> str:
    fmt = "usd0" if _is_money(spec) else "num0"
    dim = spec.dimensions[0] if spec.dimensions else None
    lines = [
        "---",
        f"title: {spec.label}",
        "queries:",
        f"  - metrics/{spec.name}.sql",
        "---",
        "",
        _context_sentence(spec),
        "",
    ]
    if spec.kind == "ratio":
        lines += [
            (
                f"> **Ratio metric.** Aggregated as `sum({spec.numerator}) / "
                f"sum({spec.denominator})` at whatever grain you group by. "
                f"Averaging the ratio itself gives a different — and wrong — answer."
            ),
            "",
        ]
    lines += [
        "```sql series",
        f"select metric_time, sum({spec.numerator}) as {spec.numerator}, "
        f"sum({spec.denominator}) as {spec.denominator}, "
        f"sum({spec.numerator}) / nullif(sum({spec.denominator}), 0) as {spec.name}"
        if spec.kind == "ratio"
        else f"select metric_time, sum({spec.name}) as {spec.name}",
        f"from ${{metrics_{spec.name}}} group by 1 order by 1",
        "```",
        "",  # a component on the line after a fence is swallowed by the block
        f"<LineChart data={{series}} x=metric_time y={spec.name} yFmt={fmt}/>",
        "",
    ]
    if dim:
        lines += [
            f"## By {dim.replace('_', ' ')}",
            "",
            "```sql by_dim",
            f"select {dim}, "
            + (
                f"sum({spec.numerator}) / nullif(sum({spec.denominator}), 0) as {spec.name}"
                if spec.kind == "ratio"
                else f"sum({spec.name}) as {spec.name}"
            ),
            f"from ${{metrics_{spec.name}}} where {dim} is not null group by 1 order by 2 desc",
            "```",
            "",
            f"<BarChart data={{by_dim}} x={dim} y={spec.name} swapXY=true xFmt={fmt}/>",
            "",
        ]
    return "\n".join(_fence_spacing(lines)) + "\n"


def _context_sentence(spec: MetricSpec) -> str:
    """What is included and excluded, in one sentence.

    A page without this forces the reader to open the SQL to know whether a
    number counts refunds — which is the moment they stop trusting the number.
    """
    parts = [spec.description.rstrip(".") if spec.description else f"The `{spec.name}` metric"]
    if spec.filter_sql:
        parts.append(f"**restricted to `{spec.filter_sql}`**")
    else:
        parts.append("**unfiltered** — every row in the underlying fact counts")
    parts.append(f"measured over `{spec.time_column}` from `{spec.model}`")
    if spec.kind == "ratio":
        parts.append(
            f"and carried as `{spec.numerator}` / `{spec.denominator}` so it re-divides correctly at any grain"
        )
    return (
        ", ".join(parts) + ". Defined once in the dbt semantic layer and "
        "compiled to `queries/metrics/` — this page does not restate it."
    )


def _fence_spacing(lines: list[str]) -> list[str]:
    """Guarantee a blank line between a closing fence and a component.

    MDsveX absorbs a component on the line directly after ``` into the code
    block's scope, and the build fails with "'QueryViewer' is not defined" —
    naming the page but not the line. Doing this as a post-pass rather than at
    each call site means a new page template cannot forget it.
    """
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        if line.strip() == "```" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("<"):
            out.append("")
    return out


def _is_money(spec: MetricSpec) -> bool:
    return any(
        t in spec.name.lower() or t in spec.label.lower()
        for t in ("revenue", "amount", "value", "volume", "mrr", "arr", "aov")
    )


def _config(project: str, warehouse: Path) -> str:
    def block(name: str, colors: list[str]) -> str:
        return f"      {name}:\n" + "".join(f"        - '{c}'\n" for c in colors)

    # Theme keys follow @evidence-dev/tailwind's zod schema: categorical
    # palettes live under `colorPalettes.default.{light,dark}`, and single
    # colors under `colors` — built-in names where a semantic match exists
    # (positive/warning/negative drive components like BigValue deltas), a
    # custom name where none does. The previous `colors.categorical` /
    # `status` shape validated as *nothing*: zod warned and dropped it, and
    # the CVD-checked palette silently never applied.
    return f"""# Generated by `pf report build`. Palette values are validated —
# adjacent-pair CVD deltaE >= 8, normal-vision >= 15, contrast checked on both
# surfaces. Re-picking them by eye makes charts unreadable for ~8% of readers.
title: {project}

plugins:
  # Both sections are load-bearing. Without `components`, Evidence's
  # injectComponents() discovers zero component plugins, silently injects no
  # imports, and every generated page dies in the build with
  # "'QueryViewer' is not defined" — naming a component no page mentions,
  # because the preprocessor wraps each sql fence in one.
  components:
    "@evidence-dev/core-components": {{}}
  datasources:
    "@evidence-dev/duckdb": {{}}

theme:
  colorPalettes:
    default:
{block("light", PALETTE_LIGHT)}{block("dark", PALETTE_DARK)}  colors:
    positive: '{STATUS["good"]}'
    warning: '{STATUS["warning"]}'
    negative: '{STATUS["critical"]}'
    status-serious: '{STATUS["serious"]}'
"""


def _source_conn(project: str, warehouse: Path) -> str:
    """Connector for the project warehouse.

    `filename` is resolved **relative to the source directory**
    (`reporting/sources/<name>/`), not the project root — an absolute path is
    appended to it and fails with a confusing "database does not exist" naming a
    concatenated path. Hence the relative walk back up.
    """
    return f"""# DuckDB connector for this project's warehouse.
# One warehouse file per project is what lets sister companies run in parallel;
# the reporting layer only ever reads.
name: {project.replace("-", "_")}
type: duckdb
options:
  filename: ../../../data/{project.replace("-", "_")}.duckdb
"""


def _row_counts(root: Path, group: str, project: str, relations: list[tuple[str, str]]) -> dict[str, int] | None:
    """Row count per (schema, name) relation, or None when the warehouse
    does not exist yet. A relation that cannot be counted (not built yet) is
    simply absent — its extract stays, and `npm run sources` reports it."""
    from pf.runtime.warehouse import Warehouse

    wh = Warehouse.for_project(root, group, project)
    if not wh.path.exists():
        return None
    counts: dict[str, int] = {}
    try:
        with wh.connect(read_only=True) as con:
            for schema, name in relations:
                try:
                    counts[name] = con.execute(f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
                except Exception:
                    continue
    except Exception:
        return None
    return counts


def build(project_dir: str | Path, group: str, project: str) -> dict[str, Any]:
    """Generate the Evidence project. Returns a summary."""
    root = Path(project_dir)
    out = root / "reporting"
    specs = collect_metrics(root)
    _, mdl = _load(root)
    schema = "main_marts"
    warehouse = (root / "data" / f"{project.replace('-', '_')}.duckdb").resolve()

    (out / "queries" / "metrics").mkdir(parents=True, exist_ok=True)
    (out / "pages" / "metrics").mkdir(parents=True, exist_ok=True)
    (out / "sources" / project.replace("-", "_")).mkdir(parents=True, exist_ok=True)

    for spec in specs:
        (out / "queries" / "metrics" / f"{spec.name}.sql").write_text(_metric_sql(spec, schema))
        (out / "pages" / "metrics" / f"{spec.name}.md").write_text(_metric_page(project, spec))

    (out / "pages" / "index.md").write_text(_index_page(project, specs))
    (out / "evidence.config.yaml").write_text(_config(project, warehouse))
    (out / "sources" / project.replace("-", "_") / "connection.yaml").write_text(_source_conn(project, warehouse))

    counts = _row_counts(
        root, group, project, [(m["tableReference"]["schema"], m["name"]) for m in mdl.get("models", [])]
    )

    extracted = 0
    skipped_empty: list[str] = []
    for model in mdl.get("models", []):
        name = model["name"]
        visible = [c["name"] for c in model["columns"] if not c.get("isHidden")]
        target = out / "sources" / project.replace("-", "_") / f"{name}.sql"
        if counts is not None and counts.get(name) == 0:
            # Evidence's duckdb connector writes a zero-row extract as a
            # zero-byte file, and duckdb-wasm then kills the whole site build
            # with "too small to be a Parquet file". An empty relation gets no
            # extract and is reported instead; it comes back the moment the
            # model has data and this build runs again.
            target.unlink(missing_ok=True)
            skipped_empty.append(name)
            continue
        if not visible:
            # Never `select *`. The old fallback did exactly that when the MDL
            # carried no visible columns — which made the comment below a lie:
            # the star re-includes every column the projection hid, PII first.
            # A model the MDL cannot enumerate gets no extract at all, and a
            # stale extract from a previous generation is removed with it.
            target.unlink(missing_ok=True)
            continue
        target.write_text(
            f"-- source extract for {name} (PII columns excluded by the MDL projection)\n"
            f"-- Columns are enumerated, never `select *`: the extract's shape is a\n"
            f"-- contract with the pages reading it, and a star changes shape silently.\n"
            f"select\n"
            + ",\n".join(f"    {c}" for c in visible)
            + f"\nfrom {model['tableReference']['schema']}.{name}\n"
        )
        extracted += 1

    # Dependency set is evidence-dev/template's package.json verbatim, not a
    # hand-assembled subset. Two earlier attempts failed here: pinning
    # core-components from a *different* project's lockfile broke every page with
    # "'QueryViewer' is not defined", and trimming connectors dropped
    # @evidence-dev/tailwind, which the generated Vite config imports. The
    # `overrides` block is what actually resolves the peer conflict — reaching for
    # legacy-peer-deps instead suppresses the error and then omits the peers the
    # build needs.
    (out / "package.json").write_text(
        json.dumps(
            {
                "name": f"{project}-reporting",
                "version": "0.0.1",
                "private": True,
                "type": "module",
                "scripts": {
                    "build": "evidence build",
                    "build:strict": "evidence build:strict",
                    "dev": "evidence dev",
                    "sources": "evidence sources",
                    "preview": "evidence preview",
                },
                "dependencies": {
                    "@evidence-dev/bigquery": "^2.0.12",
                    "@evidence-dev/core-components": "^5.4.2",
                    "@evidence-dev/csv": "^1.0.16",
                    "@evidence-dev/databricks": "^1.0.10",
                    "@evidence-dev/duckdb": "^2.0.1",
                    "@evidence-dev/evidence": "^40.1.8",
                    "@evidence-dev/motherduck": "^1.0.6",
                    "@evidence-dev/mssql": "^1.1.4",
                    "@evidence-dev/mysql": "^1.1.6",
                    "@evidence-dev/postgres": "^1.0.10",
                    "@evidence-dev/snowflake": "^1.2.4",
                    "@evidence-dev/source-javascript": "^0.0.3",
                    "@evidence-dev/sqlite": "^2.0.9",
                    "@evidence-dev/trino": "^1.0.11",
                },
                # The one peer legacy-peer-deps skips that the build genuinely needs.
                # Version comes from evidence@40.1.8's own peerDependencies, not a guess.
                "devDependencies": {
                    "@sveltejs/vite-plugin-svelte": "3.1.2",
                    # Build-time requires the template resolves from the project
                    # root, not from its own node_modules — absent, the build
                    # dies at the settings route (git-remote-origin-url) or at
                    # PostCSS config load (autoprefixer/postcss). Measured, not
                    # theoretical: both happened on the first clean build.
                    "git-remote-origin-url": "^4.0.0",
                    "autoprefixer": "^10.4.20",
                    "postcss": "^8.4.47",
                },
                "overrides": {
                    "jsonwebtoken": "9.0.0",
                    "trim@<0.0.3": ">0.0.3",
                    "sqlite3": "5.1.5",
                    "axios": "^1.7.4",
                },
            },
            indent=2,
        )
        + "\n"
    )

    # legacy-peer-deps is required on npm >= 11, which resolves Evidence's own
    # peer graph more strictly than the npm the upstream template targets. It is
    # safe *because* the dependency block above is the complete canonical set —
    # nothing the build needs is left to peer resolution.
    (out / ".npmrc").write_text("loglevel=error\naudit=false\nfund=false\nlegacy-peer-deps=true\n")

    # Toolchain note, verified by controlled experiment rather than assumed:
    # a pristine `degit evidence-dev/template` fails to build identically on
    # node 24 / npm 11, so `evidence build` failures there are Evidence's
    # supported-runtime boundary, not this generator. `evidence sources` and
    # `evidence dev` both work. Recorded next to the code so the next person
    # does not repeat the bisection.
    (out / ".nvmrc").write_text("20\n")

    return {
        "metrics": len(specs),
        "pages": len(specs) + 1,
        # What was actually written, not what the MDL listed — the two differ
        # by exactly the models whose extract was refused above.
        "sources": extracted,
        "path": out,
        "unbacked": [s.name for s in specs if not s.time_column],
        "skipped_empty": skipped_empty,
    }
