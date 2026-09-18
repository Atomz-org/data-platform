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
  * **A page re-aggregates only what composes.** Sums and counts add up, max and
    min compose with themselves, an average composes through its own sum and
    count, and a distinct count or percentile does not compose at all — so it is
    shown exactly as computed rather than summed into a wrong total.
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
PALETTE_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                 "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PALETTE_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500",
                "#d55181", "#008300", "#9085e9", "#e66767"]
STATUS = {"good": "#0ca30c", "warning": "#fab219",
          "serious": "#ec835a", "critical": "#d03b3b"}


#: MetricFlow's aggregation names are not SQL. `average(x)`, `count_distinct(x)`
#: and `sum_boolean(x)` exist in none of the warehouses this platform targets,
#: and writing the name through verbatim failed every page built on such a
#: measure — at query time, long after the build reported success.
_SQL_AGG = {"sum": "sum", "count": "count", "max": "max", "min": "min",
            "average": "avg"}

#: How a page may re-aggregate rows that were already aggregated per metric_time
#: and dimension. `ratio` means "carry a sum and a count and re-divide"; `none`
#: means no correct re-aggregation exists, so nothing is summed.
ROLLUP = {"sum": "sum", "count": "sum", "sum_boolean": "sum",
          "max": "max", "min": "min", "average": "ratio",
          "count_distinct": "none", "median": "none", "percentile": "none"}


def agg_sql(agg: str, expr: str, params: dict[str, Any] | None = None,
            where: str = "") -> str | None:
    """One MetricFlow measure as a SQL aggregate, or None for an unknown agg.

    `where` filters inside the aggregate instead of in a WHERE clause — the one
    case a WHERE cannot express is a ratio whose two sides filter differently.
    The percentile forms are the ANSI ordered-set spelling, which DuckDB,
    Snowflake and Postgres all accept.
    """
    agg = (agg or "sum").lower()
    params = params or {}
    value = f"case when {where} then {expr} end" if where else expr
    if agg in _SQL_AGG:
        return f"{_SQL_AGG[agg]}({value})"
    if agg == "count_distinct":
        return f"count(distinct {value})"
    if agg == "sum_boolean":
        cond = f"({where}) and ({expr})" if where else expr
        return f"sum(case when {cond} then 1 else 0 end)"
    if agg in ("median", "percentile"):
        pct = 0.5 if agg == "median" else float(params.get("percentile", 0.5))
        fn = "percentile_disc" if params.get("use_discrete_percentile") else "percentile_cont"
        return f"{fn}({pct}) within group (order by {value})"
    return None


@dataclass
class MetricSpec:
    name: str
    label: str
    kind: str                       # simple | ratio | derived | cumulative
    model: str                      # physical table the measure sits on
    expression: str                 # aggregate expression
    filter_sql: str = ""
    time_column: str = ""
    dimensions: list[str] = None    # categorical dimensions available
    numerator: str = ""
    denominator: str = ""
    description: str = ""
    #: How a page re-aggregates this metric — a value of ROLLUP.
    rollup: str = "sum"
    #: The aggregates carried as `numerator` / `denominator` when rollup is ratio.
    numerator_sql: str = ""
    denominator_sql: str = ""
    #: The measure behind a simple metric, so a ratio can re-render it with the
    #: metric's own filter.
    measure: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.dimensions = self.dimensions or []
        self.measure = self.measure or {}


# --------------------------------------------------------------- reading ----
def _load(project_dir: Path) -> tuple[dict, dict]:
    target = project_dir / "transform" / "target"
    sm = target / "semantic_manifest.json"
    mdl = project_dir / "mdl" / "mdl.json"
    return (json.loads(sm.read_text()) if sm.exists() else {},
            json.loads(mdl.read_text()) if mdl.exists() else {})


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


def collect_metrics(project_dir: Path,
                    skipped: list[str] | None = None) -> list[MetricSpec]:
    """Every metric the report can render. Names it cannot go to `skipped`."""
    skipped = [] if skipped is None else skipped
    sm, _ = _load(project_dir)
    if not sm:
        return []

    measures: dict[str, dict[str, Any]] = {}
    for model in sm.get("semantic_models") or []:
        table = (model.get("node_relation") or {}).get("alias") or model.get("name")
        time_col = (model.get("defaults") or {}).get("agg_time_dimension") or ""
        dims = [d["name"] for d in (model.get("dimensions") or [])
                if d.get("type") != "time"]
        for m in model.get("measures") or []:
            agg = (m.get("agg") or "sum").lower()
            expr = m.get("expr") or m["name"]
            params = m.get("agg_params") or {}
            sql = agg_sql(agg, expr, params)
            if sql is None:
                continue
            measures[m["name"]] = {
                "agg": agg, "expr": expr, "params": params, "sql": sql,
                "model": table, "time": time_col, "dims": dims,
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
                skipped.append(m["name"])  # its measure has no SQL translation
                continue
            rollup = ROLLUP.get(src["agg"], "none")
            spec = MetricSpec(name=m["name"], label=m.get("label") or m["name"],
                              kind="simple", model=src["model"],
                              expression=src["sql"], filter_sql=flt,
                              time_column=src["time"],
                              # A distinct count per segment cannot be summed back
                              # into a total, so it is grouped by time alone.
                              dimensions=src["dims"] if rollup != "none" else [],
                              description=m.get("description", ""),
                              rollup=rollup, measure=src)
            if rollup == "ratio":
                # An average travels as its own sum and count, so a page that
                # rolls days into months divides totals instead of averaging
                # averages.
                spec.numerator = f"{spec.name}__sum"
                spec.denominator = f"{spec.name}__count"
                spec.numerator_sql = agg_sql("sum", src["expr"])
                spec.denominator_sql = agg_sql("count", src["expr"])
        elif kind == "ratio":
            num = by_name.get(_metric_name(tp.get("numerator")))
            den = by_name.get(_metric_name(tp.get("denominator")))
            if not num or not den:
                skipped.append(m["name"])
                continue
            if num.filter_sql == den.filter_sql:
                where, num_sql, den_sql = num.filter_sql, num.expression, den.expression
            else:
                # One WHERE cannot hold two filters. Using the numerator's alone
                # silently applied it to the denominator too.
                where, num_sql, den_sql = "", _filtered(num), _filtered(den)
            # Re-dividing summed components is right only when both components
            # are sums. Over a distinct count or an average it would sum the
            # unsummable, so such a ratio is read exactly as computed.
            additive = num.rollup == "sum" and den.rollup == "sum"
            spec = MetricSpec(name=m["name"], label=m.get("label") or m["name"],
                              kind="ratio", model=num.model,
                              expression=f"{num_sql} / nullif({den_sql}, 0)",
                              filter_sql=where, time_column=num.time_column,
                              dimensions=num.dimensions if additive else [],
                              numerator=num.name, denominator=den.name,
                              description=m.get("description", ""),
                              rollup="ratio" if additive else "none",
                              numerator_sql=num_sql, denominator_sql=den_sql)
        else:
            # Only a derived metric that merely renames one base metric can be
            # drawn from that base. One with an offset (`price_prev`), an
            # expression over several inputs, or a cumulative window would be
            # drawn as its base under its own title — a "MoM change" page
            # plotting the price. MetricFlow computes those; the report does
            # not, and says so.
            base = _passthrough_base(kind, tp, by_name)
            if base is None:
                skipped.append(m["name"])
                continue
            spec = MetricSpec(name=m["name"], label=m.get("label") or m["name"],
                              kind=kind, model=base.model, expression=base.expression,
                              filter_sql=base.filter_sql, time_column=base.time_column,
                              dimensions=base.dimensions,
                              description=m.get("description", ""),
                              rollup=base.rollup, measure=base.measure,
                              numerator=base.numerator, denominator=base.denominator,
                              numerator_sql=base.numerator_sql,
                              denominator_sql=base.denominator_sql)
        specs.append(spec)
        by_name[spec.name] = spec
    return specs


def _passthrough_base(kind: str, tp: dict[str, Any],
                      by_name: dict[str, MetricSpec]) -> MetricSpec | None:
    """The one base metric a derived metric merely renames, or None."""
    if kind != "derived":
        return None
    inputs = tp.get("metrics") or []
    if len(inputs) != 1:
        return None
    x = inputs[0]
    if isinstance(x, dict) and (x.get("offset_window") or x.get("offset_to_grain")):
        return None
    base = by_name.get(_metric_name(x))
    if base is None:
        return None
    alias = (x.get("alias") if isinstance(x, dict) else None) or base.name
    expr = (tp.get("expr") or "").strip()
    return base if expr in ("", base.name, alias) else None


def _non_additive_reason(spec: MetricSpec) -> str:
    if spec.kind == "ratio":
        return "ratio over a non-additive component"
    return spec.measure.get("agg", spec.kind)


def _filtered(spec: MetricSpec) -> str:
    """A ratio component's aggregate with its own filter moved inside it."""
    m = spec.measure
    if not spec.filter_sql or not m:
        return spec.expression
    return agg_sql(m["agg"], m["expr"], m["params"], where=spec.filter_sql) or spec.expression


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

    head = [f"-- metric: {spec.name} ({spec.kind}) — generated by `pf report build`",
            f"-- {spec.description or spec.label}",
            "-- Do not edit. Change the metric in transform/models/semantic/, then rerun."]
    if spec.rollup == "ratio":
        head += [
            "-- Ratio rule: re-divide at the display grain —",
            f"--   sum({spec.numerator}) / sum({spec.denominator})",
            f"-- NEVER avg({spec.name}). Components are carried for exactly that.",
        ]
    elif spec.rollup == "none":
        head += [
            f"-- Not re-aggregatable ({_non_additive_reason(spec)}): grouped by",
            "-- time alone, and read exactly as computed. Never sum it.",
        ]

    body = ["select",
            f"    {spec.time_column} as metric_time{dim_sql},"]
    if spec.rollup == "ratio":
        body.append(f"    {spec.numerator_sql} as {spec.numerator},")
        body.append(f"    {spec.denominator_sql} as {spec.denominator},")
    body.append(f"    {spec.expression} as {spec.name}")
    body.append(f"from {schema}.{spec.model}{where}")
    body.append(f"group by {group_by}")
    body.append("order by 1")
    return "\n".join(head + body) + "\n"


def _rollup_sql(spec: MetricSpec) -> str | None:
    """How a page aggregates this metric's rows, or None if it must not."""
    if spec.rollup == "ratio":
        return f"sum({spec.numerator}) / nullif(sum({spec.denominator}), 0)"
    if spec.rollup in ("sum", "max", "min"):
        return f"{spec.rollup}({spec.name})"
    return None


def _index_page(project: str, specs: list[MetricSpec]) -> str:
    """Standard page anatomy: title + context -> filter row -> KPI row ->
    primary trend -> breakdown -> detail. Never a wall of charts."""
    simple = [s for s in specs if s.kind in ("simple", "ratio") and _rollup_sql(s)]
    kpis = simple[:4]
    trend = next((s for s in specs if s.kind == "simple" and _rollup_sql(s)), None)
    # The breakdown reads the trend's own query, so the dimension must be one
    # that query carries — any other spec's dimension is a missing column.
    dim = trend.dimensions[0] if trend and trend.dimensions else None

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
            f"select {_rollup_sql(s)} as {s.name}",
            f"from ${{metrics_{s.name}}}",
            "```",
            "",
        ]

    if kpis:
        lines += ["<Grid cols=" + str(min(len(kpis), 4)) + ">", ""]
        for s in kpis:
            fmt = "usd0" if _is_money(s) else "num0"
            lines.append(f"<BigValue data={{kpi_{s.name}}} value={s.name} "
                         f"title='{s.label}' fmt={fmt}/>")
        lines += ["", "</Grid>", ""]

    if trend:
        lines += [
            f"## {trend.label} over time",
            "",
            "```sql trend",
            f"select metric_time, {_rollup_sql(trend)} as {trend.name}",
            f"from ${{metrics_{trend.name}}}",
            "group by 1 order by 1",
            "```",
            (f"<LineChart data={{trend}} x=metric_time y={trend.name} "
            f"yFmt={'usd0' if _is_money(trend) else 'num0'}/>"),
            "",
        ]

    if trend and dim:
        lines += [
            f"## {trend.label} by {dim.replace('_', ' ')}",
            "",
            "```sql breakdown",
            f"select {dim}, {_rollup_sql(trend)} as {trend.name}",
            f"from ${{metrics_{trend.name}}}",
            f"where {dim} is not null",
            "group by 1 order by 2 desc",
            "```",
            (f"<BarChart data={{breakdown}} x={dim} y={trend.name} swapXY=true "
            f"xFmt={'usd0' if _is_money(trend) else 'num0'}/>"),
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
        "---", f"title: {spec.label}",
        "queries:", f"  - metrics/{spec.name}.sql", "---", "",
        _context_sentence(spec),
        "",
    ]
    rollup = _rollup_sql(spec)
    if spec.rollup == "ratio":
        kind = "Ratio metric" if spec.kind == "ratio" else "Average"
        lines += [
            (f"> **{kind}.** Aggregated as `sum({spec.numerator}) / "
            f"sum({spec.denominator})` at whatever grain you group by. "
            f"Averaging the {'ratio' if spec.kind == 'ratio' else 'average'} "
            f"itself gives a different — and wrong — answer."),
            "",
        ]
    elif rollup is None:
        lines += [
            (f"> **Not additive.** A `{_non_additive_reason(spec)}` "
             f"cannot be rebuilt from grouped rows, so the series is shown exactly "
             f"as the metric computed it, per `{spec.time_column}`."),
            "",
        ]
    if spec.rollup == "ratio":
        series = (f"select metric_time, sum({spec.numerator}) as {spec.numerator}, "
                  f"sum({spec.denominator}) as {spec.denominator}, "
                  f"{rollup} as {spec.name}")
        tail = f"from ${{metrics_{spec.name}}} group by 1 order by 1"
    elif rollup:
        series = f"select metric_time, {rollup} as {spec.name}"
        tail = f"from ${{metrics_{spec.name}}} group by 1 order by 1"
    else:
        series = f"select metric_time, {spec.name}"
        tail = f"from ${{metrics_{spec.name}}} order by 1"
    lines += [
        "```sql series",
        series,
        tail,
        "```",
        "",   # a component on the line after a fence is swallowed by the block
        f"<LineChart data={{series}} x=metric_time y={spec.name} yFmt={fmt}/>",
        "",
    ]
    if dim and rollup:
        lines += [
            f"## By {dim.replace('_', ' ')}", "",
            "```sql by_dim",
            f"select {dim}, {rollup} as {spec.name}",
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
    parts = [spec.description.rstrip(".") if spec.description
             else f"The `{spec.name}` metric"]
    if spec.filter_sql:
        parts.append(f"**restricted to `{spec.filter_sql}`**")
    else:
        parts.append("**unfiltered** — every row in the underlying fact counts")
    parts.append(f"measured over `{spec.time_column}` from `{spec.model}`")
    if spec.rollup == "ratio":
        parts.append(f"and carried as `{spec.numerator}` / `{spec.denominator}` so it "
                     f"re-divides correctly at any grain")
    return (", ".join(parts) + ". Defined once in the dbt semantic layer and "
            "compiled to `queries/metrics/` — this page does not restate it.")


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
        if line.strip() == "```" and i + 1 < len(lines) \
                and lines[i + 1].lstrip().startswith("<"):
            out.append("")
    return out


def _is_money(spec: MetricSpec) -> bool:
    return any(t in spec.name.lower() or t in spec.label.lower()
               for t in ("revenue", "amount", "value", "volume", "mrr", "arr", "aov"))


def _config(project: str, warehouse: Path) -> str:
    def block(name: str, colors: list[str]) -> str:
        return f"    {name}:\n" + "".join(f"      - '{c}'\n" for c in colors)
    return f"""# Generated by `pf report build`. Palette values are validated —
# adjacent-pair CVD deltaE >= 8, normal-vision >= 15, contrast checked on both
# surfaces. Re-picking them by eye makes charts unreadable for ~8% of readers.
title: {project}

plugins:
  datasources:
    "@evidence-dev/duckdb": {{}}

theme:
  colors:
    categorical:
{block("light", PALETTE_LIGHT)}{block("dark", PALETTE_DARK)}
  status:
""" + "".join(f"    {k}: '{v}'\n" for k, v in STATUS.items())


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
name: {project.replace('-', '_')}
type: duckdb
options:
  filename: ../../../data/{project.replace('-', '_')}.duckdb
"""


def build(project_dir: str | Path, group: str, project: str) -> dict[str, Any]:
    """Generate the Evidence project. Returns a summary."""
    root = Path(project_dir)
    out = root / "reporting"
    skipped: list[str] = []
    specs = collect_metrics(root, skipped)
    _, mdl = _load(root)
    schema = "main_marts"
    warehouse = (root / "data" / f"{project.replace('-', '_')}.duckdb").resolve()

    (out / "queries" / "metrics").mkdir(parents=True, exist_ok=True)
    (out / "pages" / "metrics").mkdir(parents=True, exist_ok=True)
    (out / "sources" / project.replace("-", "_")).mkdir(parents=True, exist_ok=True)

    for spec in specs:
        (out / "queries" / "metrics" / f"{spec.name}.sql").write_text(
            _metric_sql(spec, schema))
        (out / "pages" / "metrics" / f"{spec.name}.md").write_text(
            _metric_page(project, spec))

    # Both directories are generated in full, so a file for a metric that is
    # no longer rendered is stale, not someone's work.
    current = {s.name for s in specs}
    removed: list[str] = []
    for sub, ext in (("queries", ".sql"), ("pages", ".md")):
        for f in (out / sub / "metrics").glob(f"*{ext}"):
            if f.stem not in current:
                f.unlink()
                removed.append(f.stem)

    (out / "pages" / "index.md").write_text(_index_page(project, specs))
    (out / "evidence.config.yaml").write_text(_config(project, warehouse))
    (out / "sources" / project.replace("-", "_") / "connection.yaml").write_text(
        _source_conn(project, warehouse))

    for model in mdl.get("models", []):
        name = model["name"]
        cols = ", ".join(c["name"] for c in model["columns"] if not c.get("isHidden"))
        (out / "sources" / project.replace("-", "_") / f"{name}.sql").write_text(
            f"-- source extract for {name} (PII columns excluded by the MDL projection)\n"
            f"select {cols or '*'}\nfrom {model['tableReference']['schema']}.{name}\n")

    # Dependency set is evidence-dev/template's package.json verbatim, not a
    # hand-assembled subset. Two earlier attempts failed here: pinning
    # core-components from a *different* project's lockfile broke every page with
    # "'QueryViewer' is not defined", and trimming connectors dropped
    # @evidence-dev/tailwind, which the generated Vite config imports. The
    # `overrides` block is what actually resolves the peer conflict — reaching for
    # legacy-peer-deps instead suppresses the error and then omits the peers the
    # build needs.
    (out / "package.json").write_text(json.dumps({
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
        },
        "overrides": {
            "jsonwebtoken": "9.0.0",
            "trim@<0.0.3": ">0.0.3",
            "sqlite3": "5.1.5",
            "axios": "^1.7.4",
        },
    }, indent=2) + "\n")

    # legacy-peer-deps is required on npm >= 11, which resolves Evidence's own
    # peer graph more strictly than the npm the upstream template targets. It is
    # safe *because* the dependency block above is the complete canonical set —
    # nothing the build needs is left to peer resolution.
    (out / ".npmrc").write_text("loglevel=error\naudit=false\nfund=false\n"
                                "legacy-peer-deps=true\n")

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
        "sources": len(mdl.get("models", [])),
        "path": out,
        "unbacked": [s.name for s in specs if not s.time_column],
        "skipped": skipped,
        "removed": sorted(set(removed)),
    }
