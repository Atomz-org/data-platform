"""Conversational analytics: the planner that turns a question into a cube plan,
the repair that keeps a model honest, the HTTP API behind the Evidence Ask
page, and the page `pf report build` writes. The gate itself is tested in
test_tool_wren.py; here the rows are stubbed."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pf.tools import wren_api as w

TODAY = date(2026, 9, 26)


def _cat() -> w.Catalogue:
    cubes = [
        {"name": "fct_mcx_commodity_daily_metrics", "base": "fct_mcx_commodity_daily",
         "measures": [
             {"name": "avg_mcx_realised_vol", "label": "Avg MCX Realised Volatility (annualised)", "format": "pct1"},
             {"name": "mcx_realised_vol_total", "label": "MCX Realised Volatility (component)", "format": "num2"},
             {"name": "avg_mcx_daily_return", "label": "Avg MCX Daily Return", "format": "pct2"},
             {"name": "mcx_contango_share", "label": "Share of Sessions in Contango", "format": "pct1"},
             {"name": "mcx_turnover_inr", "label": "MCX Futures Turnover (₹)", "format": "inr"},
         ],
         "dimensions": [
             {"name": "mcx_commodity", "label": "Commodity", "values": ["crude_oil", "gold", "silver"]},
             {"name": "contract_code", "label": "Contract code", "values": ["CRUDEOIL", "GOLD", "GOLDM", "SILVER"]},
             {"name": "trend_regime", "label": "Trend regime", "values": ["downtrend", "sideways", "uptrend"]},
             {"name": "segment", "label": "Segment", "values": ["Bullion", "Energy"]},
             {"name": "is_flagship", "label": "Is flagship", "values": ["false", "true"]},
         ],
         "timeDimensions": [{"name": "trade_date", "label": "Trade date"}]},
    ]
    cat = w.Catalogue("commodity", "commodity-india", cubes, [], {m["name"]: m["format"] for m in cubes[0]["measures"]}, "")
    cat.suggestions = w.suggestions(cat)
    return cat


def _plan(q: str, previous: w.Plan | None = None) -> w.Plan:
    return w.plan_rules(q, _cat(), previous, TODAY)


# ------------------------------------------------------------------ rules --
def test_a_trend_for_named_values_is_a_series_over_a_grain_and_a_range() -> None:
    p = _plan("Monthly realised volatility for gold and silver over the last 12 months")
    assert p.measures == ["avg_mcx_realised_vol"], "the answer, not its (component) building block"
    assert p.dimensions == ["mcx_commodity"] and p.granularity == "month" and p.start == "2025-09-19"
    assert p.filters == [{"dimension": "mcx_commodity", "op": "in", "values": ["gold", "silver"]}], \
        "a value binds to one dimension — `gold` is not also the contract code GOLD"
    assert w.validate(p, _cat()) is None


def test_a_word_of_the_measure_is_not_a_grain_and_this_year_is_a_range_not_a_series() -> None:
    p = _plan("average daily return by segment this year")
    assert p.measures == ["avg_mcx_daily_return"] and p.dimensions == ["segment"]
    assert p.granularity == "" and p.start == "2026-01-01", "'daily return' is the measure; 'this year' a period"
    _, time_dim, filters = w.cube_args(p)
    assert time_dim == "" and filters == ["trade_date:gte:2026-01-01", "trade_date:lte:2026-09-26"], \
        "a period without a grain filters — one total per segment, not a row per day"


def test_a_ranking_orders_and_limits_and_finds_its_breakdown() -> None:
    p = _plan("top 2 commodities by contango share")
    assert (p.measures, p.dimensions, p.order_by, p.descending, p.limit) == \
        (["mcx_contango_share"], ["mcx_commodity"], "mcx_contango_share", True, 2)


def test_a_dimension_word_is_not_a_measure_word_or_a_trend() -> None:
    p = _plan("Futures turnover by trend regime")
    assert p.measures == ["mcx_turnover_inr"] and p.dimensions == ["trend_regime"] and not p.granularity


def test_a_follow_up_refines_the_previous_plan() -> None:
    first = _plan("Monthly realised volatility for gold and silver over the last 12 months")
    p = _plan("now for flagship contracts only", first)
    assert p.measures == first.measures and p.granularity == "month"
    assert {"dimension": "is_flagship", "op": "eq", "values": ["true"]} in p.filters


def test_an_unrelated_question_asks_rather_than_guesses() -> None:
    p = _plan("what is the weather", _plan("average daily return by segment"))
    assert p.kind == "clarify" and "Which measure" in p.clarify


def test_the_plan_reads_back_in_words() -> None:
    p = _plan("Monthly realised volatility for gold and silver over the last 12 months")
    assert w.describe(p, _cat()) == ("Avg MCX Realised Volatility (annualised) · by commodity · monthly · "
                                     "2025-09-19 to 2026-09-26 · commodity: gold, silver")


def test_suggestions_are_sentences_from_the_catalogue() -> None:
    s = _cat().suggestions
    assert s and s[0].startswith("Top 5 commodities by ")
    assert not any("(component)" in x or "mcx commodity" in x for x in s)


# ------------------------------------------------------------ model plans --
def test_repair_removes_what_the_question_never_asked_for() -> None:
    """A model plan that adds "the past week" to a question with no period
    answers a different question. Taken out before validation, not hoped for."""
    cat = _cat()
    p = w.Plan(cube="fct_mcx_commodity_daily_metrics", measures=["mcx_contango_share"], dimensions=["mcx_commodity"],
               time_dimension="trade_date", granularity="", start="2026-09-19", end="2026-09-26",
               order_by="mcx_contango_share", limit=5, planner="claude-cli")
    r = w.repair(p, "Top 5 commodities by contango share", cat)
    assert (r.start, r.end, r.time_dimension, r.order_by) == ("", "", "", "mcx_contango_share")
    p = w.Plan(cube="fct_mcx_commodity_daily_metrics", measures=["avg_mcx_realised_vol"], time_dimension="trade_date",
               granularity="month", order_by="trade_date", planner="claude-cli")
    assert w.repair(p, "monthly realised volatility", cat).order_by == "", "a series is already in time order"


def test_a_plan_naming_what_the_cube_lacks_is_refused_before_it_runs() -> None:
    cat = _cat()
    assert "no measure" in w.validate(w.Plan(cube="fct_mcx_commodity_daily_metrics", measures=["nope"]), cat)
    assert "no cube" in w.validate(w.Plan(cube="nope", measures=["x"]), cat)
    bad = w.Plan(cube="fct_mcx_commodity_daily_metrics", measures=["mcx_contango_share"],
                 filters=[{"dimension": "mcx_commodity", "op": "equals", "values": ["gold"]}])
    assert "operator" in w.validate(bad, cat)


def test_the_first_planner_that_validates_wins_and_the_others_are_reported(monkeypatch) -> None:
    monkeypatch.setattr(w, "planners_available", lambda: ["claude-cli", "rules"])
    monkeypatch.setattr(w, "plan_claude_cli", lambda *a, **k: w.Plan(cube="nope", measures=["x"], planner="claude-cli"))
    p, notes = w.plan("top 2 commodities by contango share", _cat(), today=TODAY)
    assert p.planner == "rules" and notes == ["claude-cli: plan refused — no cube `nope`"]


def test_the_chart_follows_the_form_of_the_answer() -> None:
    t = {"name": "trade_date__month", "kind": "time"}
    d = {"name": "mcx_commodity", "kind": "dimension"}
    m = {"name": "v", "kind": "measure"}
    series = [{"trade_date__month": f"2026-0{i}-01", "mcx_commodity": c, "v": i} for i in (1, 2) for c in ("a", "b")]
    assert w.chart_hint([t, d, m], series) == "line"
    assert w.chart_hint([d, m], [{"mcx_commodity": "a", "v": 1}, {"mcx_commodity": "b", "v": 2}]) == "bar"
    assert w.chart_hint([m], [{"v": 1}]) == "number"
    one_period = [{"trade_date__month": "2026-01-01", "mcx_commodity": c, "v": 1} for c in "ab"]
    assert w.chart_hint([t, d, m], one_period) == "bar", "one period is a ranking, not a line"


# ------------------------------------------------------------------- http --
@pytest.fixture()
def client(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(w, "catalogue", lambda *a, **k: _cat())
    monkeypatch.setattr(w, "planners_available", lambda: ["rules"])
    monkeypatch.setattr(w, "run", lambda d, g, p, plan, cat, root=None: {
        "ok": True, "stage": "done", "message": "", "run_id": "abc12345", "attempt": 1, "planned_sql": "select 1",
        "sql": "select 1", "columns": [], "rows": [], "truncated": False, "limit": 200, "chart": "none"})
    return TestClient(w.create_app(tmp_path, "commodity", "commodity-india"))


def test_the_api_answers_and_admits_only_a_local_page(client) -> None:
    assert client.get("/api/health").json()["planners"] == ["rules"]
    r = client.post("/api/ask", json={"question": "top 2 commodities by contango share"}).json()
    assert r["ok"] and r["planner"] == "rules" and r["run_id"] == "abc12345"
    local = client.options("/api/ask", headers={"Origin": "http://localhost:4789", "Access-Control-Request-Method": "POST"})
    foreign = client.options("/api/ask", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert local.headers.get("access-control-allow-origin") == "http://localhost:4789"
    assert "access-control-allow-origin" not in foreign.headers


def test_the_builder_refuses_a_plan_the_cube_cannot_run(client) -> None:
    assert client.post("/api/cube", json={"cube": "fct_mcx_commodity_daily_metrics", "measures": ["nope"]}).status_code == 400
    ok = client.post("/api/cube", json={"cube": "fct_mcx_commodity_daily_metrics", "measures": ["mcx_contango_share"],
                                        "dimensions": ["mcx_commodity"]}).json()
    assert ok["interpretation"] == "Share of Sessions in Contango · by commodity"


def test_only_a_read_can_be_remembered(client) -> None:
    assert client.post("/api/remember", json={"question": "x", "sql": "drop table t"}).status_code == 400


# ------------------------------------------------------------------- page --
def test_report_build_writes_the_ask_page_only_where_a_workspace_can_serve_it(tmp_path: Path) -> None:
    from pf.projections import evidence

    root = tmp_path / "p"
    (root / "reporting" / "pages").mkdir(parents=True)
    assert evidence.write_ask_page(root, "g", "p") is False
    assert not (root / "reporting" / "pages" / "ask.md").exists()
    (root / "mdl" / "wren").mkdir(parents=True)
    (root / "mdl" / "wren" / "wren_project.yml").write_text("name: p\n")
    assert evidence.write_ask_page(root, "g", "p") is True
    page = (root / "reporting" / "pages" / "ask.md").read_text()
    component = (root / "reporting" / "components" / "WrenChat.svelte").read_text()
    assert '<WrenChat group="g" project="p" />' in page and "uv run pf tool wren api g p" in page
    assert f"/*PALETTE_LIGHT*/ {json.dumps(evidence.PALETTE_LIGHT)} /*END*/" in component, \
        "the chat draws with the validated palette the dashboards use, in its order"
    (root / "mdl" / "wren" / "wren_project.yml").unlink()
    evidence.write_ask_page(root, "g", "p")
    assert not (root / "reporting" / "pages" / "ask.md").exists(), "no workspace, no page pointing at nothing"


def test_the_ask_page_passes_the_report_audit(tmp_path: Path) -> None:
    from pf.projections import evidence
    from pf.projections.report_audit import audit

    root = tmp_path / "p"
    (root / "mdl" / "wren").mkdir(parents=True)
    (root / "mdl" / "wren" / "wren_project.yml").write_text("name: p\n")
    evidence.write_ask_page(root, "g", "p")
    _, findings = audit(root)
    assert not [f for f in findings if f.page == "pages/ask.md" and f.severity in ("error", "warning")]


# ------------------------------------------------------- any project, many --
def _generic_cat() -> w.Catalogue:
    """A catalogue from a different domain, with its own source prefix."""
    ms = [{"name": f"acme_{n}", "label": lbl, "format": f} for n, lbl, f in (
        ("revenue_total", "Revenue", "usd"), ("order_count", "Orders", "num0"),
        ("avg_basket", "Avg Basket Size", "usd"), ("refund_rate", "Refund Rate", "pct1"))]
    cube = {"name": "fct_orders_metrics", "base": "fct_orders", "measures": ms,
            "dimensions": [{"name": "region", "label": "Region", "values": ["EMEA", "NA"]},
                           {"name": "channel", "label": "Channel", "values": ["retail", "web"]}],
            "timeDimensions": [{"name": "ordered_at", "label": "Ordered at"}]}
    cat = w.Catalogue("acme", "acme-us", [cube], [], {m["name"]: m["format"] for m in ms}, "")
    cat.noise = w.noise_words(cat)
    cat.suggestions = w.suggestions(cat)
    return cat


def test_nothing_about_one_project_is_written_into_the_planner() -> None:
    """The source prefix a project's measures share is learned from its own
    catalogue, so the same planner reads a retail workspace as well as MCX."""
    cat = _generic_cat()
    assert cat.noise == {"acme"}
    p = w.plan_rules("monthly refund rate for web by region", cat, None, TODAY)
    assert p.measures == ["acme_refund_rate"] and p.dimensions == ["region"] and p.granularity == "month"
    assert p.filters == [{"dimension": "channel", "op": "eq", "values": ["web"]}]
    assert cat.suggestions and not any(word in " ".join(cat.suggestions).lower() for word in ("gold", "mcx", "commodit"))


def _project(root: Path, g: str, p: str, *, mdl: bool = True, workspace: bool = True) -> Path:
    d = root / "groups" / g / "projects" / p
    (d / "mdl" / "wren").mkdir(parents=True)
    if workspace:
        (d / "mdl" / "wren" / "wren_project.yml").write_text(f"name: {p}\n")
    if mdl:
        (d / "mdl" / "mdl.json").write_text(json.dumps({"models": [], "cubes": []}))
    return d


def test_every_project_with_a_workspace_is_served_and_nothing_else(tmp_path: Path) -> None:
    _project(tmp_path, "acme", "acme-us")
    _project(tmp_path, "acme", "acme-eu")
    _project(tmp_path, "zenith", "zenith-uk")
    _project(tmp_path, "zenith", "zenith-de", workspace=False)
    assert [s.key for s in w.discover(tmp_path)] == ["acme/acme-eu", "acme/acme-us", "zenith/zenith-uk"]
    assert [s.key for s in w.discover(tmp_path, "acme")] == ["acme/acme-eu", "acme/acme-us"]
    assert [s.key for s in w.discover(tmp_path, "acme", "acme-us")] == ["acme/acme-us"]


def test_a_project_that_cannot_answer_says_what_its_owner_runs(tmp_path: Path, monkeypatch) -> None:
    s = w.Served("globex", "globex-eu", _project(tmp_path, "globex", "globex-eu", mdl=False))
    st = w.status(s)
    assert not st["ready"] and "pf semantic mdl globex globex-eu" in st["fix"]
    empty = w.Catalogue("globex", "globex-core", [], [], {}, "")
    monkeypatch.setattr(w, "catalogue", lambda *a, **k: empty)
    s2 = w.Served("globex", "globex-core", _project(tmp_path, "globex", "globex-core"))
    st2 = w.status(s2)
    assert not st2["ready"] and "pf seed globex globex-core" in st2["fix"]


def test_one_process_serves_many_projects_and_each_answers_only_for_itself(tmp_path: Path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    cats = {"commodity-india": _cat(), "acme-us": _generic_cat()}
    monkeypatch.setattr(w, "catalogue", lambda d, g, p: cats[p])
    monkeypatch.setattr(w, "planners_available", lambda: ["rules"])
    seen = []
    monkeypatch.setattr(w, "run", lambda d, g, p, plan, cat, root=None: (seen.append((g, p, plan.cube)) or {
        "ok": True, "stage": "done", "message": "", "run_id": "r", "attempt": 1, "planned_sql": "", "sql": "",
        "columns": [], "rows": [], "truncated": False, "limit": 200, "chart": "none"}))
    served = [w.Served("commodity", "commodity-india", _project(tmp_path, "commodity", "commodity-india")),
              w.Served("acme", "acme-us", _project(tmp_path, "acme", "acme-us"))]
    client = TestClient(w.create_app(served))
    assert {p["project"] for p in client.get("/api/projects").json()["projects"]} == {"commodity-india", "acme-us"}
    a = client.post("/api/p/acme/acme-us/ask", json={"question": "refund rate by region"}).json()
    b = client.post("/api/p/commodity/commodity-india/ask", json={"question": "top 2 commodities by contango share"}).json()
    assert a["plan"]["cube"] == "fct_orders_metrics" and b["plan"]["cube"] == "fct_mcx_commodity_daily_metrics"
    assert seen == [("acme", "acme-us", "fct_orders_metrics"), ("commodity", "commodity-india", "fct_mcx_commodity_daily_metrics")]
    # one project's catalogue never leaks into another's
    assert client.get("/api/p/acme/acme-us/catalog").json()["cubes"][0]["base"] == "fct_orders"
    other = client.get("/api/p/globex/globex-eu/health")
    assert other.status_code == 404 and other.json()["detail"]["served"] == ["acme/acme-us", "commodity/commodity-india"]
    assert client.get("/api/health").status_code == 404, "no unscoped routes when more than one project is served"


def test_every_page_calls_only_its_own_project() -> None:
    from pf.projections.evidence import ask_component

    text = ask_component()
    assert "/api/p/${encodeURIComponent(group)}/${encodeURIComponent(project)}" in text
    for word in ("gold", "silver", "crude", "MCX", "commodit"):
        assert word not in text, f"`{word}` is one project's vocabulary in every project's page"


def test_the_harness_counts_the_ask_page_as_generated_not_yours() -> None:
    """The project's harness map separates what a person owns from what a
    generator rewrites; the Ask page is the latter wherever it was written."""
    from conftest import REPO_ROOT
    from pf.harnessmap import gather_report

    r = gather_report(REPO_ROOT, "commodity", "commodity-india")
    assert any("pages/ask.md" in what for what, _ in r.generated)
    assert "pages/ask.md" not in r.owned and "components/" not in r.owned
