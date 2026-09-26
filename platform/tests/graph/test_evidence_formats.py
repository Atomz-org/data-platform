"""Number formats in the reporting layer: declared, rendered, and audited.

The standard (viz-standards → Number formats) is that a figure states its unit
correctly and fits its tile: a count never wears a currency, a rupee never wears
a dollar, and a money total auto-scales instead of printing fifteen digits. It
broke in exactly those three ways on commodity-india's overview — lots shown as
`$399,443,006`, rupees as `usd0`, and `507,206,987,230,000` overflowing a tile.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pf.projections.evidence import (
    _index_page,
    _metric_sql,
    build,
    collect_metrics,
    format_family,
    kpi_format,
    metric_format,
)
from pf.projections.report_audit import audit, format_findings


@pytest.mark.parametrize(("name", "label", "meta", "expected"), [
    # Declared beats inferred.
    ("turnover", "Turnover", {"format": "inr0k"}, "inr0k"),
    ("turnover", "Turnover", {"unit": "INR"}, "inr"),
    ("hit_rate", "Hit Rate", {"unit": "pct"}, "pct1"),
    ("volume_lots", "Volume", {"unit": "lots"}, "num0"),
    ("generation", "Generation", {"unit": "mwh"}, "num0"),
    # A currency symbol in the label.
    ("oi_value", "Open Interest Value (₹)", None, "inr"),
    # An ISO code as a word of the name or label.
    ("period_high_price_usd", "Period High (USD)", None, "usd"),
    ("landed_price_inr", "Landed Price", None, "inr"),
    ("retry_count", "Retries", None, "num0"),
    # The regression: volume was a money word, so lots rendered as dollars.
    ("mcx_commodity_volume_flagship_lots", "Volume (flagship-lot equivalents)", None, "num0"),
    ("sessions", "Sessions", None, "num0"),
    # Projects that never declared a currency render exactly as before.
    ("revenue", "Revenue", None, "usd0"),
    ("avg_price", "Avg Price", None, "num0"),
])
def test_metric_format_resolution(name, label, meta, expected) -> None:
    assert metric_format(name, label, meta) == expected


@pytest.mark.parametrize(("fmt", "family"), [
    ("inr", "inr"), ("inr0k", "inr"), ("'inr2'", "inr"), ("usd0", "usd"),
    ("pct1", "pct"), ("num0", "num"), ("#,##0.00", "num"), ("", "num"),
    # A sized tile code, and the same code after a page's quotes are stripped.
    ('\'"₹"#,##0.00,,,,"T"\'', "inr"), ('₹"#,##0.0,,,"B', "inr"), ('#,##0.0,,"M"', "num"),
])
def test_format_family(fmt, family) -> None:
    assert format_family(fmt) == family


def test_a_kpi_tile_always_auto_scales_money() -> None:
    assert kpi_format("usd0") == "usd"
    assert kpi_format("inr2") == "inr"
    assert kpi_format("pct1") == "pct1"
    assert kpi_format("num0") == "num0"


@pytest.mark.parametrize(("fmt", "magnitude", "rendered"), [
    # The three tiles that overflowed on commodity-india's overview.
    ("inr", 485_087_892_696_000, "₹485.09T"),
    ("inr", 3_752_956_197_250, "₹3.75T"),
    ("inr", 720_871_683_236, "₹720.9B"),
    ("num0", 399_443_006, "399.4M"),
    ("usd0", 720_871_683, "$720.9M"),
    ("inr", 52_000, "₹52.0k"),
    ("inr", 950, "₹950"),
    ("num0", 950, "950"),
    ("pct1", 0.42, "42.0%"),
])
def test_a_tile_is_sized_to_its_number(fmt, magnitude, rendered) -> None:
    """Rendered with the formatter Evidence itself uses (SheetJS `ssf`), when node
    and the project's node_modules are present."""
    import shutil
    import subprocess

    code = kpi_format(fmt, magnitude).strip("'")
    assert format_family(code) == format_family(fmt)          # the unit never changes
    root = Path(__file__).resolve().parents[3]
    ssf = next(root.glob("groups/*/projects/*/reporting/node_modules/ssf"), None)
    if not (shutil.which("node") and ssf):
        pytest.skip("node, or any project's Evidence install (ssf), is missing")
    reporting = ssf.parent.parent
    excel = {"pct1": "0.0%", "num0": "#,##0"}.get(code, code)
    script = "const s=require('ssf');console.log(s.format(process.argv[1],Number(process.argv[2])))"
    out = subprocess.run(["node", "-e", script, excel, str(magnitude)],
                         cwd=reporting, capture_output=True, text=True, check=True).stdout.strip()
    assert out == rendered


def _project(tmp_path: Path) -> Path:
    manifest = {
        "semantic_models": [{
            "name": "sessions",
            "node_relation": {"alias": "fct_sessions"},
            "defaults": {"agg_time_dimension": "trade_date"},
            "dimensions": [{"name": "trade_date", "type": "time"},
                           {"name": "commodity", "type": "categorical"}],
            "measures": [
                {"name": "turnover_sum", "agg": "sum", "expr": "turnover_inr"},
                {"name": "lots_sum", "agg": "sum", "expr": "volume_lots"},
            ],
        }],
        "metrics": [
            {"name": "turnover_inr", "label": "Futures Turnover (₹)", "type": "simple",
             "type_params": {"measure": {"name": "turnover_sum"}},
             "config": {"meta": {"unit": "INR"}}},
            {"name": "volume_lots", "label": "Volume (lots)", "type": "simple",
             "type_params": {"measure": {"name": "lots_sum"}},
             "config": {"meta": {"unit": "lots"}}},
        ],
    }
    target = tmp_path / "transform" / "target"
    target.mkdir(parents=True)
    (target / "semantic_manifest.json").write_text(json.dumps(manifest))
    return tmp_path


def test_declared_units_reach_every_rendered_component(tmp_path: Path) -> None:
    specs = {s.name: s for s in collect_metrics(_project(tmp_path))}
    assert specs["turnover_inr"].fmt == "inr"
    assert specs["volume_lots"].fmt == "num0"
    page = _index_page("demo", list(specs.values()))
    assert "value=turnover_inr title='Futures Turnover (₹)' fmt=inr/>" in page
    assert "value=volume_lots title='Volume (lots)' fmt=num0/>" in page
    assert "usd" not in page
    assert "-- format: inr" in _metric_sql(specs["turnover_inr"], "demo")


def test_the_generated_report_passes_its_own_format_audit(tmp_path: Path) -> None:
    project = _project(tmp_path)
    build(project, "g", "demo")
    _, findings = audit(project)
    assert not [f for f in findings if f.rule.startswith("fmt-")], findings


DECLARED = {"turnover_inr": "inr", "volume_lots": "num0", "hit_rate": "pct1"}


@pytest.mark.parametrize(("tag", "rule"), [
    # A count wearing a currency.
    ("<BigValue data={k} value=volume_lots fmt=usd0/>", "fmt-unit"),
    # A rupee wearing a dollar.
    ("<LineChart data={s} x=metric_time y=turnover_inr yFmt=usd/>", "fmt-unit"),
    # A share shown as a raw decimal.
    ("<BarChart data={b} x=commodity y=hit_rate xFmt=num2/>", "fmt-unit"),
    # Money with no format at all: Evidence prints every digit.
    ("<BigValue data={k} value=turnover_inr/>", "fmt-missing"),
    # Money fixed to whole rupees in a tile: fifteen digits.
    ("<BigValue data={k} value=turnover_inr fmt=inr0/>", "fmt-unscaled"),
])
def test_the_audit_catches_a_wrong_format(tag, rule) -> None:
    assert [f.rule for f in format_findings("p.md", tag, DECLARED)] == [rule]


@pytest.mark.parametrize("tag", [
    "<BigValue data={k} value=turnover_inr fmt=inr/>",
    "<BigValue data={k} value=turnover_inr fmt=inr1b/>",
    "<LineChart data={s} x=metric_time y=turnover_inr yFmt=inr0/>",
    "<BigValue data={k} value=volume_lots fmt=num0/>",
    "<BarChart data={b} x=commodity y=hit_rate xFmt=pct0/>",
    # Not a metric column: a page's own derived figure is its own business.
    "<BigValue data={k} value=turnover_crore fmt=num0/>",
    "<LineChart data={s} x=trade_date y={['close_price','ema_9']} yFmt='#,##0'/>",
    # What `pf report build` writes for a sized tile.
    """<BigValue data={k} value=turnover_inr fmt='"₹"#,##0.00,,,,"T"'/>""",
])
def test_the_audit_accepts_a_right_format(tag) -> None:
    assert format_findings("p.md", tag, DECLARED) == []


def test_a_ratio_compiles_whatever_order_the_manifest_lists_it_in(tmp_path: Path) -> None:
    """dbt's metric order is not ours: a ratio listed before its components was
    silently skipped, and pages referencing it broke on the next unrelated edit."""
    project = _project(tmp_path)
    sm_path = project / "transform" / "target" / "semantic_manifest.json"
    sm = json.loads(sm_path.read_text())
    sm["metrics"].insert(0, {"name": "lots_per_rupee", "label": "Lots per Rupee",
                             "type": "ratio",
                             "type_params": {"numerator": {"name": "volume_lots"},
                                             "denominator": {"name": "turnover_inr"}}})
    sm_path.write_text(json.dumps(sm))
    skipped: list[str] = []
    names = {s.name for s in collect_metrics(project, skipped)}
    assert "lots_per_rupee" in names, skipped


def test_a_ratios_components_are_not_headline_tiles(tmp_path: Path) -> None:
    project = _project(tmp_path)
    sm_path = project / "transform" / "target" / "semantic_manifest.json"
    sm = json.loads(sm_path.read_text())
    sm["metrics"].append({"name": "lots_per_rupee", "label": "Lots per Rupee", "type": "ratio",
                          "type_params": {"numerator": {"name": "volume_lots"},
                                          "denominator": {"name": "turnover_inr"}}})
    sm_path.write_text(json.dumps(sm))
    page = _index_page("demo", collect_metrics(project))
    assert "value=lots_per_rupee" in page
    assert "value=volume_lots" not in page and "value=turnover_inr" not in page


def test_a_stock_is_read_at_its_latest_day_not_summed_over_time(tmp_path: Path) -> None:
    """Open interest summed over a year is 250 snapshots added together. A
    measure declared non-additive over time becomes a `stock`: summed across
    dimensions within a day, read at the latest day on tiles and breakdowns,
    and still usable inside a ratio (put/call on notional open interest)."""
    import duckdb
    from pf.projections.evidence import _metric_page

    project = _project(tmp_path)
    sm_path = project / "transform" / "target" / "semantic_manifest.json"
    sm = json.loads(sm_path.read_text())
    model = sm["semantic_models"][0]
    model["measures"] += [
        {"name": "oi_sum", "agg": "sum", "expr": "oi_inr",
         "non_additive_dimension": {"name": "trade_date", "window_choice": "max"}},
        {"name": "put_oi_sum", "agg": "sum", "expr": "put_oi_inr",
         "non_additive_dimension": {"name": "trade_date", "window_choice": "max"}},
    ]
    sm["metrics"] += [
        {"name": "oi_value", "label": "Open Interest (₹)", "type": "simple",
         "type_params": {"measure": {"name": "oi_sum"}}, "config": {"meta": {"unit": "INR"}}},
        {"name": "put_oi", "label": "Put OI (component)", "type": "simple",
         "type_params": {"measure": {"name": "put_oi_sum"}}},
        {"name": "put_share", "label": "Put Share of OI", "type": "ratio",
         "type_params": {"numerator": {"name": "put_oi"}, "denominator": {"name": "oi_value"}}},
    ]
    sm_path.write_text(json.dumps(sm))
    specs = {s.name: s for s in collect_metrics(project)}
    assert specs["oi_value"].rollup == "stock"
    assert specs["put_share"].rollup == "ratio"          # a ratio of stocks re-divides

    con = duckdb.connect()
    con.execute("create schema demo")
    con.execute("create table demo.fct_sessions as select * from (values "
                "(date '2026-09-23', 'gold', 100.0, 40.0, 1.0, 1.0), "
                "(date '2026-09-24', 'gold', 120.0, 60.0, 1.0, 1.0), "
                "(date '2026-09-24', 'silver', 30.0, 10.0, 1.0, 1.0)) "
                "t(trade_date, commodity, oi_inr, put_oi_inr, turnover_inr, volume_lots)")
    compiled = f"({_metric_sql(specs['oi_value'], 'demo')})"
    # Without the ratio, whose denominator it is (and so off the headline row).
    page = _index_page("demo", [specs["oi_value"], specs["volume_lots"]])
    kpi = page.split("```sql kpi_oi_value", 1)[1].split("```", 1)[0]
    total = con.execute(kpi.replace("${metrics_oi_value}", compiled)).fetchone()[0]
    assert total == 150.0                                 # the latest day, both commodities

    by_dim = _metric_page("demo", specs["oi_value"]).split("```sql by_dim", 1)[1].split("```", 1)[0]
    rows = dict(con.execute(by_dim.replace("${metrics_oi_value}", compiled)).fetchall())
    assert rows == {"gold": 120.0, "silver": 30.0}        # not 220 for gold
