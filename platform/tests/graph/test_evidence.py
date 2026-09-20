"""The Evidence projection, executed rather than string-matched.

Every assertion below runs the SQL the projection writes against DuckDB. A
query that merely looks right is what shipped before: `average(price)` read
naturally in review and failed on the first page load.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import duckdb
import pytest
from pf.projections.evidence import (
    _index_page,
    _metric_page,
    _metric_sql,
    _rollup_sql,
    agg_sql,
    build,
    collect_metrics,
)

# Two days with different row counts, so an average of daily averages (35) and
# the true average (27.5) disagree.
ROWS = [
    ("p1", "2026-01-01", "a", 10.0, "ok", True),
    ("p2", "2026-01-01", "a", 20.0, "ok", False),
    ("p3", "2026-01-01", "b", 30.0, "void", True),
    ("p4", "2026-01-02", "b", 50.0, "ok", True),
]


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    c.execute("create schema main_marts")
    c.execute("create table main_marts.fct_prices (price_id varchar, price_date date, "
              "segment varchar, price double, status varchar, is_listed boolean)")
    c.executemany("insert into main_marts.fct_prices values (?, ?, ?, ?, ?, ?)", ROWS)
    yield c
    c.close()


@pytest.mark.parametrize(("agg", "params", "expected"), [
    ("sum", {}, 110.0),
    ("count", {}, 4),
    ("max", {}, 50.0),
    ("min", {}, 10.0),
    ("average", {}, 27.5),
    ("count_distinct", {}, 4),
    ("median", {}, 25.0),
    ("percentile", {"percentile": 0.75, "use_discrete_percentile": True}, 30.0),
])
def test_every_metricflow_aggregation_is_valid_sql(con, agg, params, expected) -> None:
    sql = agg_sql(agg, "price", params)
    assert con.sql(f"select {sql} from main_marts.fct_prices").fetchone()[0] == expected


def test_sum_boolean_counts_true_rows(con) -> None:
    sql = agg_sql("sum_boolean", "is_listed")
    assert con.sql(f"select {sql} from main_marts.fct_prices").fetchone()[0] == 3


def test_a_filter_moves_inside_the_aggregate(con) -> None:
    sql = agg_sql("sum", "price", where="status = 'ok'")
    assert con.sql(f"select {sql} from main_marts.fct_prices").fetchone()[0] == 80.0


def test_an_unknown_aggregation_is_refused_not_guessed() -> None:
    assert agg_sql("geometric_mean", "price") is None


def _measure(name: str, agg: str, expr: str, **params) -> dict:
    return {"name": name, "agg": agg, "expr": expr, "agg_params": params or None}


def _metric(name: str, kind: str, filter_sql: str = "", **type_params) -> dict:
    out = {"name": name, "label": name, "type": kind, "type_params": type_params}
    if filter_sql:
        out["filter"] = {"where_filters": [{"where_sql_template": filter_sql}]}
    return out


@pytest.fixture()
def specs(tmp_path: Path) -> dict:
    manifest = {
        "semantic_models": [{
            "name": "prices",
            "node_relation": {"alias": "fct_prices"},
            "defaults": {"agg_time_dimension": "price_date"},
            "dimensions": [{"name": "price_date", "type": "time"},
                           {"name": "segment", "type": "categorical"}],
            "measures": [
                _measure("price_mean", "average", "price"),
                _measure("price_high", "max", "price"),
                _measure("price_total", "sum", "price"),
                _measure("price_rows", "count", "price_id"),
                _measure("price_ids", "count_distinct", "price_id"),
            ],
        }],
        "metrics": [
            _metric("avg_price", "simple", measure={"name": "price_mean"}),
            _metric("high_price", "simple", measure={"name": "price_high"}),
            _metric("distinct_prices", "simple", measure={"name": "price_ids"}),
            _metric("ok_total", "simple",
                    "{{ Dimension('price__status') }} = 'ok'",
                    measure={"name": "price_total"}),
            _metric("all_rows", "simple", measure={"name": "price_rows"}),
            _metric("ok_total_per_row", "ratio",
                    numerator={"name": "ok_total"}, denominator={"name": "all_rows"}),
            _metric("avg_price_growth", "derived",
                    metrics=[{"name": "avg_price"}], expr="avg_price"),
            # A ratio whose numerator cannot be summed.
            _metric("uniq_per_row", "ratio",
                    numerator={"name": "distinct_prices"}, denominator={"name": "all_rows"}),
            # A real month-over-month change: an offset the report cannot draw.
            _metric("price_mom", "derived",
                    metrics=[{"name": "avg_price", "alias": "p"},
                             {"name": "avg_price", "alias": "p_prev",
                              "offset_window": {"count": 1, "granularity": "month"}}],
                    expr="(p - p_prev) / nullif(p_prev, 0)"),
        ],
    }
    _write(tmp_path, manifest)
    return {s.name: s for s in collect_metrics(tmp_path)}


def _write(tmp_path: Path, manifest: dict) -> None:
    target = tmp_path / "transform" / "target"
    target.mkdir(parents=True, exist_ok=True)
    (target / "semantic_manifest.json").write_text(json.dumps(manifest))


def _run(con, spec) -> str:
    """The compiled query, as the subquery a page reads it through."""
    return f"({_metric_sql(spec, 'main_marts')})"


def _page_query(page: str, block: str, spec, con) -> list[tuple]:
    sql = re.search(rf"```sql {block}\n(.*?)\n```", page, re.S).group(1)
    return con.sql(sql.replace(f"${{metrics_{spec.name}}}", _run(con, spec))).fetchall()


def test_every_compiled_query_executes(con, specs) -> None:
    for spec in specs.values():
        con.sql(_metric_sql(spec, "main_marts")).fetchall()


def test_an_average_rolls_up_through_its_sum_and_count(con, specs) -> None:
    spec = specs["avg_price"]
    assert spec.rollup == "ratio"
    total = con.sql(f"select {_rollup_sql(spec)} from {_run(con, spec)}").fetchone()[0]
    assert total == 27.5, "an average of the daily averages would be 35"


def test_max_rolls_up_with_max_not_sum(con, specs) -> None:
    spec = specs["high_price"]
    total = con.sql(f"select {_rollup_sql(spec)} from {_run(con, spec)}").fetchone()[0]
    assert total == 50.0


def test_a_distinct_count_is_never_summed(con, specs) -> None:
    spec = specs["distinct_prices"]
    assert spec.rollup == "none" and spec.dimensions == []
    page = _metric_page("p", spec)
    assert "sum(distinct_prices)" not in page
    assert _page_query(page, "series", spec, con) == [
        (date(2026, 1, 1), 3),
        (date(2026, 1, 2), 1),
    ]


def test_a_ratio_keeps_each_sides_own_filter(con, specs) -> None:
    spec = specs["ok_total_per_row"]
    assert spec.filter_sql == "", "a shared WHERE would filter the denominator too"
    total = con.sql(f"select {_rollup_sql(spec)} from {_run(con, spec)}").fetchone()[0]
    assert total == 80.0 / 4


def test_pages_execute_against_their_queries(con, specs) -> None:
    for name in ("avg_price", "high_price", "ok_total_per_row", "avg_price_growth"):
        spec = specs[name]
        page = _metric_page("p", spec)
        assert _page_query(page, "series", spec, con)
        assert _page_query(page, "by_dim", spec, con)


def test_the_overview_skips_what_cannot_be_totalled(specs) -> None:
    page = _index_page("p", list(specs.values()))
    assert "kpi_distinct_prices" not in page
    assert "avg(" not in page


def test_a_ratio_over_a_distinct_count_is_not_re_aggregated(specs) -> None:
    """sum(distinct counts) / sum(rows) is not a ratio of anything."""
    s = specs["uniq_per_row"]
    assert s.rollup == "none" and s.dimensions == [] and _rollup_sql(s) is None
    assert "kpi_uniq_per_row" not in _index_page("p", list(specs.values()))
    assert specs["ok_total_per_row"].rollup == "ratio"  # sums still re-divide


def test_a_derived_metric_with_an_offset_is_skipped_and_named(specs, tmp_path: Path) -> None:
    skipped: list[str] = []
    names = {s.name for s in collect_metrics(tmp_path, skipped)}
    assert skipped == ["price_mom"]
    assert "price_mom" not in names
    assert "avg_price_growth" in names  # a bare alias of one base still renders


def test_build_removes_pages_for_metrics_it_no_longer_renders(specs, tmp_path: Path) -> None:
    out = tmp_path / "reporting"
    for sub, ext in (("queries", "sql"), ("pages", "md")):
        (out / sub / "metrics").mkdir(parents=True)
        (out / sub / "metrics" / f"price_mom.{ext}").write_text("stale")
    r = build(tmp_path, "g", "p")
    assert r["skipped"] == ["price_mom"] and r["removed"] == ["price_mom"]
    assert not (out / "pages" / "metrics" / "price_mom.md").exists()
    assert (out / "pages" / "metrics" / "uniq_per_row.md").exists()


# ------------------------------------------------------------- exposures ----

def test_every_page_that_reads_something_becomes_a_dbt_exposure(specs, tmp_path: Path) -> None:
    """The loop was open here: pages consumed marts and lineage could not see it.

    `pf impact` on a column reported nothing downstream while a dashboard was
    reading it, so the owner of a broken page was never told.
    """
    import yaml
    (tmp_path / "transform" / "models").mkdir(parents=True, exist_ok=True)
    build(tmp_path, "g", "p")
    doc = yaml.safe_load(
        (tmp_path / "transform" / "models" / "_reporting__exposures.yml").read_text())
    by_name = {e["name"]: e for e in doc["exposures"]}
    assert "report_metrics_ok_total_per_row" in by_name
    exp = by_name["report_metrics_ok_total_per_row"]
    assert exp["depends_on"] == ["ref('fct_prices')"]
    assert exp["type"] == "dashboard" and exp["owner"]["email"]


def test_a_curated_page_reading_a_source_extract_is_an_exposure_too(specs, tmp_path: Path) -> None:
    """A page can reach the warehouse without a metric — `from <source>.<table>`.
    That is still a dependency, and it is the shape every hand-written board has."""
    import yaml
    (tmp_path / "transform" / "models").mkdir(parents=True, exist_ok=True)
    build(tmp_path, "g", "p")
    page = tmp_path / "reporting" / "pages" / "board.md"
    page.write_text("---\ntitle: Board\n---\n\n```sql b\nselect * from p.rpt_board\n```\n")
    build(tmp_path, "g", "p")
    doc = yaml.safe_load(
        (tmp_path / "transform" / "models" / "_reporting__exposures.yml").read_text())
    exp = next(e for e in doc["exposures"] if e["name"] == "report_board")
    assert exp["depends_on"] == ["ref('rpt_board')"]
    assert exp["url"] == "reporting/pages/board.md"


def test_a_page_that_reads_nothing_gets_no_exposure(specs, tmp_path: Path) -> None:
    import yaml
    (tmp_path / "transform" / "models").mkdir(parents=True, exist_ok=True)
    build(tmp_path, "g", "p")
    (tmp_path / "reporting" / "pages" / "about.md").write_text(
        "---\ntitle: About\n---\n\nJust prose, no query.\n")
    build(tmp_path, "g", "p")
    doc = yaml.safe_load(
        (tmp_path / "transform" / "models" / "_reporting__exposures.yml").read_text())
    assert "report_about" not in {e["name"] for e in doc["exposures"]}


def test_the_generated_theme_uses_the_keys_evidence_actually_reads(tmp_path: Path) -> None:
    """An earlier shape nested the palette under `theme.colors.categorical` —
    valid YAML that Evidence ignores, so every chart rendered in the stock
    palette while the config claimed a validated one."""
    import yaml
    from pf.projections.evidence import PALETTE_LIGHT, _config
    theme = yaml.safe_load(_config("p", tmp_path / "p.duckdb"))["theme"]
    assert theme["colorPalettes"]["default"]["light"] == PALETTE_LIGHT
    assert theme["colorScales"]["default"]["dark"]
    # Status colours are Evidence's reserved names, not ours.
    assert set(theme["colors"]) >= {"positive", "negative", "warning", "info"}


def test_the_group_manifest_owner_shape_is_accepted(tmp_path: Path) -> None:
    """`group.yaml` spells this team/contact; dbt spells it name/email. Falling
    back to a placeholder address is how an exposure ends up telling nobody."""
    from pf.projections.evidence import _owner
    root = tmp_path / "groups" / "g" / "projects" / "p"
    root.mkdir(parents=True)
    (tmp_path / "groups" / "g" / "group.yaml").write_text(
        "owner:\n  team: commodity-research\n  contact: research@example.com\n")
    assert _owner(root) == {"name": "commodity-research",
                            "email": "research@example.com"}


def test_a_metric_query_addresses_the_evidence_source_not_the_warehouse_schema(
        specs, tmp_path: Path) -> None:
    """The two namespaces look interchangeable and are not.

    A source extract runs against the warehouse connection, so it selects
    `main_marts.<model>`. A file in `queries/` runs against the extracted
    parquet, where the only namespace is the source's. Writing the warehouse
    schema into a metric query compiled, scored 100 on the mechanical audit, and
    executed correctly against DuckDB by hand — then failed *every* query at
    `evidence build` with "Table with name fct_prices does not exist". Nothing
    short of a real build caught it, so this test pins the spelling.
    """
    mdl = tmp_path / "mdl"
    mdl.mkdir()
    (mdl / "mdl.json").write_text(json.dumps({"models": [{
        "name": "fct_prices",
        "tableReference": {"schema": "main_marts", "table": "fct_prices"},
        "columns": [{"name": "price"}],
    }]}))
    build(tmp_path, "g", "my-project")
    query = (tmp_path / "reporting" / "queries" / "metrics"
             / "ok_total_per_row.sql").read_text()
    assert "from my_project.fct_prices" in query
    assert "main_marts" not in query

    extract = (tmp_path / "reporting" / "sources" / "my_project"
               / "fct_prices.sql").read_text()
    assert "from main_marts.fct_prices" in extract


def test_the_build_dependencies_cover_what_evidences_template_needs(tmp_path: Path) -> None:
    """npm >= 11 stopped hoisting four modules Evidence's own template requires.
    Without them `evidence build` dies before rendering a single page."""
    from pf.projections.evidence import build as _build
    (tmp_path / "transform" / "target").mkdir(parents=True)
    (tmp_path / "transform" / "target" / "semantic_manifest.json").write_text("{}")
    _build(tmp_path, "g", "p")
    deps = json.loads((tmp_path / "reporting" / "package.json").read_text())["dependencies"]
    assert {"git-remote-origin-url", "autoprefixer", "postcss"} <= set(deps)
    # v4 removed `tailwindcss/nesting`, which the template's postcss config imports.
    assert deps["tailwindcss"].startswith("^3")
