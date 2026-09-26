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
#: Sequential ramp for magnitude (heatmaps, colorscale table columns). One hue,
#: light->dark; reversed on the dark surface so "near zero" recedes into it.
SCALE_LIGHT = ["#cde2fb", "#3987e5", "#0d366b"]
SCALE_DARK = ["#104281", "#3987e5", "#9ec5f4"]

#: Named theme colours. Evidence reads `positive`/`negative`/`warning`/`info` for
#: deltas and alerts; they are reserved and never reused as a series colour.
COLORS = {
    "primary": ("#256abf", "#3987e5"),
    "accent": ("#eb6834", "#d95926"),
    "base": ("#ffffff", "#09090b"),
    "info": ("#2a78d6", "#3987e5"),
    "positive": ("#0ca30c", "#0ca30c"),
    "warning": ("#fab219", "#fab219"),
    "negative": ("#d03b3b", "#d03b3b"),
}


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
    #: Evidence format code every page renders this metric with (`metric_format`).
    fmt: str = "num0"

    def __post_init__(self) -> None:
        self.dimensions = self.dimensions or []
        self.measure = self.measure or {}


# ---------------------------------------------------------------- formats ----
#: Currencies Evidence formats natively (`builtInFormats.js`, `primaryCode`).
#: The bare code auto-scales with the column's magnitude (₹507.2T, not
#: 507,206,987,230,000), which is what a KPI tile needs; `<code>0` / `<code>2`
#: fix the decimals for a price, where scaling would hide the tick.
CURRENCY_FORMATS: frozenset[str] = frozenset({
    "usd", "eur", "gbp", "jpy", "cny", "inr", "krw", "chf", "cad", "aud", "nzd",
    "sgd", "hkd", "sek", "nok", "dkk", "pln", "brl", "mxn", "zar", "aed", "sar",
    "try", "rub", "idr", "thb", "myr", "php", "vnd", "ils", "czk", "huf", "ron",
    "clp", "cop", "pen", "ars", "egp", "ngn", "kes", "pkr", "bdt", "twd", "lkr",
})
_SYMBOLS = {"₹": "inr", "$": "usd", "€": "eur", "£": "gbp", "¥": "jpy"}
#: A count is never money, whatever else its name says: `volume` was on the
#: money list, and lots rendered as dollars.
_COUNT_WORDS = ("volume", "lots", "sessions", "days", "count", "contracts",
                "quantity", "units", "orders", "customers")
_MONEY_WORDS = ("revenue", "amount", "value", "mrr", "arr", "aov", "turnover")
_PERCENT_UNITS = ("pct", "percent", "%", "share", "rate")


def format_family(fmt: str) -> str:
    """`inr`, `inr0k`, `inr2`, `"₹"#,##0.0,,"M"` → `inr`; `pct1` → `pct`;
    anything else → `num`."""
    raw = str(fmt or "")
    for symbol, code in _SYMBOLS.items():
        if symbol in raw:                   # however the page quoted the code
            return code
    code = raw.strip().strip("'\"").lower()
    head = re.match(r"[a-z]+", code)
    word = head.group(0) if head else ""
    if word in CURRENCY_FORMATS:
        return word
    return "pct" if word == "pct" else "num"


def metric_format(name: str, label: str, meta: dict[str, Any] | None = None) -> str:
    """The Evidence format a metric is rendered with, everywhere it appears.

    Declared beats inferred:
      1. `meta.format` — an Evidence format code, used as written;
      2. `meta.unit` — an ISO currency (auto-scaling currency format), a percent
         unit (`pct1`), or any other unit (lots, sessions, mwh): a plain number,
         never a currency;
      3. a currency symbol in the label (`Turnover (₹)`);
      4. the name: a count word wins over a money word, and a money word with no
         declared currency keeps the old `usd0` so projects that never declared
         one render exactly as before.
    """
    meta = meta or {}
    if meta.get("format"):
        return str(meta["format"])
    unit = str(meta.get("unit") or "").strip().lower()
    if unit:
        if unit in CURRENCY_FORMATS:
            return unit
        if unit in _PERCENT_UNITS:
            return "pct1"
        return "num0"
    text = f"{name} {label}".lower()
    if any(w in text for w in _COUNT_WORDS):
        return "num0"
    for symbol, code in _SYMBOLS.items():
        if symbol in (label or ""):
            return code
    # An ISO code as a word of the name or label: `price_usd`, `Period High (USD)`.
    # `try` and `cop` are left out: as words they mean "attempt" and "police".
    words = set(re.findall(r"[a-z]+", text.replace("_", " ")))
    code = next((w for w in sorted(words) if w in CURRENCY_FORMATS - {"try", "cop"}), None)
    if code:
        return code
    if any(w in text for w in _MONEY_WORDS):
        return "usd0"
    return "num0"


_SCALES = ((1e12, ",,,,", "T"), (1e9, ",,,", "B"), (1e6, ",,", "M"), (1e4, ",", "k"))


def kpi_format(fmt: str, magnitude: float | None = None) -> str:
    """The format a KPI tile uses: one number, sized to fit.

    A tile shows a single total, often the largest on the page, and Evidence's
    auto-scaling currency code does not scale inside a `<BigValue>` — the raw
    `507,206,987,230,000` overflows it. Given the value's magnitude (measured
    at build), money and plain numbers get an explicit Excel-style scale:
    `₹485.09T`, `₹3,753.0B`, `399.4M`. Without one, a currency falls back to
    its auto code. Percentages pass through.
    """
    family = format_family(fmt)
    if family == "pct":
        return fmt
    if magnitude is None or magnitude != magnitude:            # None or NaN
        return family if family in CURRENCY_FORMATS else fmt
    symbol = next((s for s, c in _SYMBOLS.items() if c == family), None)
    prefix = f'"{symbol}"' if symbol else (f'"{family.upper()} "' if family != "num" else "")
    for floor, commas, suffix in _SCALES:
        if abs(magnitude) >= floor:
            decimals = "0.00" if suffix == "T" else "0.0"
            return f"'{prefix}#,##{decimals}{commas}\"{suffix}\"'"
    if family == "num":
        return fmt
    return f"'{prefix}#,##0'" if symbol else f"{family}0"


# --------------------------------------------------------------- reading ----
def _load(project_dir: Path) -> tuple[dict, dict]:
    target = project_dir / "transform" / "target"
    sm = target / "semantic_manifest.json"
    mdl = project_dir / "mdl" / "mdl.json"
    return (json.loads(sm.read_text(encoding="utf-8")) if sm.exists() else {},
            json.loads(mdl.read_text(encoding="utf-8")) if mdl.exists() else {})


_DIM_REF = re.compile(r"\{\{\s*Dimension\(\s*'([^']+)'\s*\)\s*\}\}")


def translate_filter(f: str) -> str:
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
            nad = (m.get("non_additive_dimension") or {}).get("name")
            measures[m["name"]] = {
                "agg": agg, "expr": expr, "params": params, "sql": sql,
                "model": table, "time": time_col, "dims": dims,
                # A stock (open interest, a balance): additive across the
                # categorical dimensions on one day, never across days.
                "stock": bool(nad) and nad == time_col,
            }

    specs: list[MetricSpec] = []
    by_name: dict[str, MetricSpec] = {}
    # Inputs before the metrics built on them. A ratio resolves its numerator
    # and denominator from `by_name`, which only holds what came earlier — and
    # the manifest's metric order is dbt's, not ours. Walking it as written
    # compiled a ratio when its components happened to precede it and silently
    # skipped it when an unrelated yml edit reshuffled them.
    order = {"simple": 0, "ratio": 1}
    for m in sorted(sm.get("metrics") or [],
                    key=lambda m: order.get((m.get("type") or "simple").lower(), 2)):
        tp = m.get("type_params") or {}
        kind = (m.get("type") or "simple").lower()
        flt = translate_filter(_filter_text(m.get("filter")))

        if kind == "simple":
            measure = _measure_name(tp.get("measure"))
            src = measures.get(measure)
            if not src:
                skipped.append(m["name"])  # its measure has no SQL translation
                continue
            rollup = ROLLUP.get(src["agg"], "none")
            if rollup == "sum" and src.get("stock"):
                rollup = "stock"
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
            additive = num.rollup in ("sum", "stock") and den.rollup in ("sum", "stock")
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
        spec.fmt = metric_format(m["name"], m.get("label") or "",
                                 (m.get("config") or {}).get("meta"))
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
    """Compile one metric to a query Evidence can run.

    `schema` is the **Evidence source name**, not the warehouse schema. The two
    look interchangeable and are not: a source extract under `sources/<name>/`
    runs against the warehouse connection, so it selects `main_marts.<model>`,
    but a file in `queries/` runs against the extracted parquet, where the only
    namespace that exists is the source's. Writing the warehouse schema here
    compiled, passed the mechanical audit, and executed correctly against DuckDB
    by hand — then failed every single query at `evidence build` with "Table with
    name fct_commodity_prices_daily does not exist".
    """
    where = f"\nwhere {spec.filter_sql}" if spec.filter_sql else ""
    dims = list(spec.dimensions)[:3]
    dim_sql = "".join(f",\n    {d}" for d in dims)
    group_by = ", ".join(str(i + 1) for i in range(1 + len(dims)))

    head = [f"-- metric: {spec.name} ({spec.kind}) — generated by `pf report build`",
            f"-- {spec.description or spec.label}",
            "-- Do not edit. Change the metric in transform/models/semantic/, then rerun.",
            # Read by `report_audit` to check every page renders it this way.
            f"-- format: {spec.fmt}"]
    if spec.rollup == "ratio":
        head += [
            "-- Ratio rule: re-divide at the display grain —",
            f"--   sum({spec.numerator}) / sum({spec.denominator})",
            f"-- NEVER avg({spec.name}). Components are carried for exactly that.",
        ]
    elif spec.rollup == "stock":
        head += [
            "-- A stock: sums across dimensions within one day, never across days.",
            "-- Read it at a day (the latest, for a total) — never sum it over time.",
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
    """How a page aggregates this metric's rows, or None if it must not.

    A `stock` sums across dimensions within a day; every caller that spans
    days reads it at the latest one (`_as_of_latest`)."""
    if spec.rollup == "ratio":
        return f"sum({spec.numerator}) / nullif(sum({spec.denominator}), 0)"
    if spec.rollup in ("sum", "max", "min"):
        return f"{spec.rollup}({spec.name})"
    if spec.rollup == "stock":
        return f"sum({spec.name})"
    return None


def _as_of_latest(spec: MetricSpec) -> str:
    """The WHERE that pins a stock to its latest day — a total of open interest
    over a year of sessions is 250 snapshots added together."""
    if spec.rollup != "stock":
        return ""
    return (f" where metric_time = (select max(metric_time) "
            f"from ${{metrics_{spec.name}}})")


def _index_page(project: str, specs: list[MetricSpec],
                magnitudes: dict[str, float] | None = None) -> str:
    """Standard page anatomy: title + context -> filter row -> KPI row ->
    primary trend -> breakdown -> detail. Never a wall of charts."""
    # A ratio's numerator and denominator exist to be re-divided, not read: a
    # tile titled "Range Position (component)" is a sum nobody asked for. The
    # headline row and the trend are drawn from metrics a person reads.
    # A label ending "(component)" is the same statement made by the author.
    components = {n for s in specs if s.kind == "ratio" for n in (s.numerator, s.denominator)}
    components |= {s.name for s in specs if "(component)" in (s.label or "").lower()}
    simple = [s for s in specs if s.kind in ("simple", "ratio") and _rollup_sql(s)
              and s.name not in components]
    kpis = simple[:4]
    trend = next((s for s in specs if s.kind == "simple" and _rollup_sql(s)
                  and s.name not in components), None)
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
            f"from ${{metrics_{s.name}}}{_as_of_latest(s)}",
            "```",
            "",
        ]

    if kpis:
        lines += ["<Grid cols=" + str(min(len(kpis), 4)) + ">", ""]
        for s in kpis:
            lines.append(f"<BigValue data={{kpi_{s.name}}} value={s.name} "
                         f"title='{s.label}' "
                         f"fmt={kpi_format(s.fmt, (magnitudes or {}).get(s.name))}/>")
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
            f"yFmt={trend.fmt}/>"),
            "",
        ]

    if trend and dim:
        lines += [
            f"## {trend.label} by {dim.replace('_', ' ')}",
            "",
            "```sql breakdown",
            f"select {dim}, {_rollup_sql(trend)} as {trend.name}",
            f"from ${{metrics_{trend.name}}}{_as_of_latest(trend)}",
            f"{'and' if _as_of_latest(trend) else 'where'} {dim} is not null",
            "group by 1 order by 2 desc",
            "```",
            (f"<BarChart data={{breakdown}} x={dim} y={trend.name} swapXY=true "
            f"xFmt={trend.fmt}/>"),
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
    fmt = spec.fmt
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
            (f"from ${{metrics_{spec.name}}}{_as_of_latest(spec)} "
             f"{'and' if _as_of_latest(spec) else 'where'} {dim} is not null "
             f"group by 1 order by 2 desc"),
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


def _config(project: str, warehouse: Path) -> str:
    """Evidence project config.

    The theme keys are Evidence's, not ours: the categorical palette lives at
    `theme.colorPalettes.default`, the sequential ramp at
    `theme.colorScales.default`, and named colours at `theme.colors.<name>`,
    each as a `{light, dark}` pair. An earlier shape here nested the palette
    under `theme.colors.categorical` — valid YAML that Evidence silently ignores,
    so every chart rendered in the stock palette while the config claimed
    otherwise. A theme that is not read is worse than no theme: it reports a
    guarantee it is not making.
    """
    def pair(name: str, light: str, dark: str, indent: str) -> str:
        return (f"{indent}{name}:\n"
                f"{indent}  light: '{light}'\n"
                f"{indent}  dark: '{dark}'\n")

    def ramp(light: list[str], dark: list[str], indent: str) -> str:
        out = f"{indent}default:\n{indent}  light:\n"
        out += "".join(f"{indent}    - '{c}'\n" for c in light)
        out += f"{indent}  dark:\n"
        out += "".join(f"{indent}    - '{c}'\n" for c in dark)
        return out

    return f"""# Generated by `pf report build`. Palette values are validated —
# adjacent-pair CVD deltaE >= 8, normal-vision >= 15, contrast checked on both
# surfaces (#ffffff light, #09090b dark). Re-picking them by eye makes charts
# unreadable for ~8% of readers, and slot ORDER is the CVD-safety mechanism:
# never reorder, never append. Light-mode slots 3-5 (aqua, yellow, magenta) are
# below 3:1 on white — a chart leaning on them needs visible labels or a
# companion table.
title: {project}

appearance:
  default: system
  switcher: true

plugins:
  components:
    "@evidence-dev/core-components": {{}}
  datasources:
    "@evidence-dev/duckdb": {{}}

theme:
  colorPalettes:
{ramp(PALETTE_LIGHT, PALETTE_DARK, "    ")}  colorScales:
{ramp(SCALE_LIGHT, SCALE_DARK, "    ")}  colors:
{"".join(pair(n, lt, dk, "    ") for n, (lt, dk) in COLORS.items())}"""


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


# ------------------------------------------------------------- exposures ----
#: A page reads the warehouse two ways: through a compiled metric
#: (`${metrics_<name>}`) or straight from a source extract
#: (`from <source>.<table>`). Both are dependencies; only the first was ever
#: visible to lineage.
_PAGE_METRIC = re.compile(r"\$\{metrics_(\w+)\}")


def _page_sources(text: str, source: str) -> set[str]:
    return set(re.findall(rf"\bfrom\s+{re.escape(source)}\.(\w+)", text, re.I))


def _exposures(out: Path, project: str, group: str, specs: list[MetricSpec],
               owner: dict[str, str]) -> str:
    """A dbt exposure per rendered page.

    Without this the loop is open at exactly the point it matters. Marts, metrics
    and MDL are all in the graph; the pages that consume them are not, so
    `pf impact` on a column reports "nothing downstream" while a dashboard is
    reading it. An exposure is the only dbt object that says *a person looks at
    this*, and a generated page deserves one as much as a hand-written one —
    more, since nobody remembers to declare what a generator wrote.

    Written into the dbt project rather than `reporting/`, because it is dbt that
    must parse it. It lands one parse behind: `pf report build` writes the file,
    the next dbt parse picks it up, and the graph build after that sees the
    edges. That is the same lag every generated dbt artefact has.
    """
    model_of = {s.name: s.model for s in specs}
    source = project.replace("-", "_")
    blocks: list[str] = []

    for page in sorted((out / "pages").rglob("*.md")):
        rel = page.relative_to(out / "pages")
        text = page.read_text(encoding="utf-8")
        title = next((ln.split(":", 1)[1].strip().strip("'\"")
                      for ln in text.splitlines()[:12] if ln.startswith("title:")),
                     page.stem)
        deps = {model_of[m] for m in _PAGE_METRIC.findall(text) if m in model_of}
        deps |= _page_sources(text, source)
        if not deps:
            # A page that reads nothing is a landing page, not an exposure.
            continue
        name = "report_" + str(rel.with_suffix("")).replace("/", "_").replace("-", "_")
        refs = "\n".join(f"      - ref('{d}')" for d in sorted(deps))
        blocks.append(
            f"  - name: {name}\n"
            f"    label: {json.dumps(title, ensure_ascii=False)}\n"
            f"    type: dashboard\n"
            f"    maturity: high\n"
            f"    url: reporting/pages/{rel.as_posix()}\n"
            f"    description: >\n"
            f"      Evidence page generated by `pf report build`. Edit the metric or the\n"
            f"      page, never this file.\n"
            f"    depends_on:\n{refs}\n"
            f"    owner:\n"
            f"      name: {json.dumps(owner['name'], ensure_ascii=False)}\n"
            f"      email: {json.dumps(owner['email'])}\n")

    if not blocks:
        # dbt refuses a schema file whose `exposures` key holds nothing —
        # "the value of 'exposures' is not a list" — and that one parse error
        # takes down every command that reads the manifest, `pf kg check`
        # included. A project whose pages read nothing yet gets no file.
        return ""
    return (
        "# Generated by `pf report build` — do not edit.\n"
        "#\n"
        "# One exposure per Evidence page, so `pf impact` on a column or a model\n"
        "# reaches the dashboards that read it and names who to tell. Deleting a\n"
        "# page removes its exposure on the next build; editing this file by hand\n"
        "# is overwritten.\n"
        f"# group: {group}  project: {project}\n"
        "version: 2\n\nexposures:\n" + "\n".join(blocks))


def _owner(root: Path) -> dict[str, str]:
    """Owner for a generated exposure, from the group manifest."""
    fallback = {"name": "Data Platform", "email": "data-platform@example.com"}
    manifest = root.parent.parent / "group.yaml"
    if not manifest.exists():
        return fallback
    try:
        import yaml
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except Exception:
        return fallback
    owner = data.get("owner")
    if isinstance(owner, dict):
        # `group.yaml` spells this team/contact; dbt spells it name/email. Accept
        # both rather than silently falling back to a placeholder address, which
        # is how an exposure ends up telling nobody.
        name = owner.get("name") or owner.get("team")
        email = owner.get("email") or owner.get("contact")
        return {"name": str(name or fallback["name"]),
                "email": str(email or fallback["email"])}
    if isinstance(owner, str):
        return {"name": owner,
                "email": str(data.get("email") or data.get("contact")
                             or fallback["email"])}
    return fallback


def _kpi_magnitudes(root: Path, group: str, project: str, specs: list[MetricSpec],
                    mdl: dict[str, Any]) -> dict[str, float]:
    """Each tile-able metric's headline value, computed the way its tile will
    compute it, so the tile's format can be sized to it (`kpi_format`). Empty
    without a warehouse — tiles then keep the auto code."""
    from pf.runtime.warehouse import Warehouse

    schemas = {m["name"]: m["tableReference"]["schema"] for m in mdl.get("models", [])}
    wh = Warehouse.for_project(root, group, project)
    if not wh.path.exists():
        return {}
    out: dict[str, float] = {}
    try:
        with wh.connect(read_only=True) as con:
            for s in specs:
                rollup = _rollup_sql(s)
                if not rollup or s.model not in schemas:
                    continue
                q = f"({_metric_sql(s, schemas[s.model])})"
                where = (f" where metric_time = (select max(metric_time) from {q})"
                         if s.rollup == "stock" else "")
                try:
                    value = con.execute(f"select {rollup} from {q}{where}").fetchone()[0]
                except Exception:  # noqa: BLE001 — a metric that cannot be measured keeps the auto code
                    continue
                if value is not None:
                    out[s.name] = float(value)
    except Exception:  # noqa: BLE001 — the report builds without a warehouse
        return {}
    return out


def _row_counts(root: Path, group: str, project: str,
                relations: list[tuple[str, str]]) -> dict[str, int] | None:
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
                    counts[name] = con.execute(
                        f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
                except Exception:
                    continue
    except Exception:
        return None
    return counts


ASSETS = Path(__file__).with_name("evidence_assets")
_PALETTE_SLOT = re.compile(r"/\*(PALETTE_LIGHT|PALETTE_DARK)\*/.*?/\*END\*/", re.S)


def ask_component() -> str:
    """The conversational component, with this platform's validated palette in
    it — the same slots, in the same order, as `evidence.config.yaml`."""
    import json as _json

    text = (ASSETS / "WrenChat.svelte").read_text(encoding="utf-8")
    values = {"PALETTE_LIGHT": PALETTE_LIGHT, "PALETTE_DARK": PALETTE_DARK}
    return _PALETTE_SLOT.sub(lambda m: f"/*{m.group(1)}*/ {_json.dumps(values[m.group(1)])} /*END*/", text)


def ask_page(group: str, project: str) -> str:
    return (
        "---\n"
        "title: Ask the data\n"
        "---\n\n"
        "<!-- GENERATED by `pf report build` (Wren workspace present). "
        f"API: uv run pf tool wren api {group} {project} -->\n\n"
        f"Ask {project}'s data a question in plain words: a measure, a breakdown, a period, what to include. "
        "Each answer is planned through the semantic layer, run read-only and recorded in the group's ledger, "
        "and shows the SQL behind it. Governed KPIs keep their metric pages.\n\n"
        "<script>\n"
        "\timport WrenChat from '$lib/WrenChat.svelte';\n"
        "</script>\n\n"
        f'<WrenChat group="{group}" project="{project}" />\n'
    )


def write_ask_page(root: Path, group: str, project: str) -> bool:
    """`pages/ask.md` and `components/WrenChat.svelte`, for a project whose Wren
    workspace exists; both removed when it does not, so a page never points at
    an API the project cannot serve."""
    out = root / "reporting"
    page, component = out / "pages" / "ask.md", out / "components" / "WrenChat.svelte"
    if not (root / "mdl" / "wren" / "wren_project.yml").is_file():
        page.unlink(missing_ok=True)
        component.unlink(missing_ok=True)
        return False
    component.parent.mkdir(parents=True, exist_ok=True)
    page.parent.mkdir(parents=True, exist_ok=True)
    component.write_text(ask_component(), encoding="utf-8")
    page.write_text(ask_page(group, project), encoding="utf-8")
    return True


def build(project_dir: str | Path, group: str, project: str) -> dict[str, Any]:
    """Generate the Evidence project. Returns a summary."""
    root = Path(project_dir)
    out = root / "reporting"
    skipped: list[str] = []
    specs = collect_metrics(root, skipped)
    _, mdl = _load(root)
    source = project.replace("-", "_")
    warehouse = (root / "data" / f"{project.replace('-', '_')}.duckdb").resolve()

    (out / "queries" / "metrics").mkdir(parents=True, exist_ok=True)
    (out / "pages" / "metrics").mkdir(parents=True, exist_ok=True)
    (out / "sources" / project.replace("-", "_")).mkdir(parents=True, exist_ok=True)

    for spec in specs:
        (out / "queries" / "metrics" / f"{spec.name}.sql").write_text(
            _metric_sql(spec, source), encoding="utf-8")
        (out / "pages" / "metrics" / f"{spec.name}.md").write_text(
            _metric_page(project, spec), encoding="utf-8")

    # Both directories are generated in full, so a file for a metric that is
    # no longer rendered is stale, not someone's work.
    current = {s.name for s in specs}
    removed: list[str] = []
    for sub, ext in (("queries", ".sql"), ("pages", ".md")):
        for f in (out / sub / "metrics").glob(f"*{ext}"):
            if f.stem not in current:
                f.unlink()
                removed.append(f.stem)

    (out / "pages" / "index.md").write_text(
        _index_page(project, specs, _kpi_magnitudes(root, group, project, specs, mdl)),
        encoding="utf-8")
    (out / "evidence.config.yaml").write_text(_config(project, warehouse), encoding="utf-8")
    asked = write_ask_page(root, group, project)
    (out / "sources" / project.replace("-", "_") / "connection.yaml").write_text(
        _source_conn(project, warehouse), encoding="utf-8")

    counts = _row_counts(
        root, group, project,
        [(m["tableReference"]["schema"], m["name"]) for m in mdl.get("models", [])])

    extracted = 0
    skipped_empty: list[str] = []
    for model in mdl.get("models", []):
        name = model["name"]
        visible = [c["name"] for c in model["columns"] if not c.get("isHidden")]
        target = out / "sources" / source / f"{name}.sql"
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
            + f"\nfrom {model['tableReference']['schema']}.{name}\n", encoding="utf-8")
        extracted += 1

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
            # Not connectors: the four modules Evidence's own template requires
            # at build time and npm >= 11 no longer hoists into the project root.
            # Without them `evidence build` dies in order — first
            # `git-remote-origin-url` from the settings endpoint, then
            # `autoprefixer` and `postcss` from the template's postcss config.
            # tailwindcss is pinned to 3: the config imports
            # `tailwindcss/nesting`, which v4 removed from its exports map.
            "autoprefixer": "^10.4.20",
            "git-remote-origin-url": "^4.0.0",
            "postcss": "^8.4.49",
            "tailwindcss": "^3.4.17",
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
    }, indent=2) + "\n", encoding="utf-8")

    # legacy-peer-deps is required on npm >= 11, which resolves Evidence's own
    # peer graph more strictly than the npm the upstream template targets. It is
    # safe *because* the dependency block above is the complete canonical set —
    # nothing the build needs is left to peer resolution.
    (out / ".npmrc").write_text("loglevel=error\naudit=false\nfund=false\n"
                                "legacy-peer-deps=true\n", encoding="utf-8")

    # Toolchain note, verified by controlled experiment rather than assumed:
    # a pristine `degit evidence-dev/template` fails to build identically on
    # node 24 / npm 11, so `evidence build` failures there are Evidence's
    # supported-runtime boundary, not this generator. `evidence sources` and
    # `evidence dev` both work. Recorded next to the code so the next person
    # does not repeat the bisection.
    (out / ".nvmrc").write_text("20\n", encoding="utf-8")

    exposures = root / "transform" / "models" / "_reporting__exposures.yml"
    if (root / "transform" / "models").exists():
        text = _exposures(out, project, group, specs, _owner(root))
        if text:
            exposures.write_text(text, encoding="utf-8")
        else:
            # Nothing to declare — and a leftover file from a build that had
            # something to declare is now a parse error, not a stale fact.
            exposures.unlink(missing_ok=True)

    return {
        "metrics": len(specs),
        "pages": sum(1 for _ in (out / "pages").rglob("*.md")),
        # What was actually written, not what the MDL listed — the two differ
        # by exactly the models whose extract was refused above.
        "sources": extracted,
        "path": out,
        "unbacked": [s.name for s in specs if not s.time_column],
        "skipped": skipped,
        "removed": sorted(set(removed)),
        "skipped_empty": skipped_empty,
        "exposures": exposures if exposures.exists() else None,
        "ask_page": asked,
    }
