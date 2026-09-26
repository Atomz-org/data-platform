"""Wren: the workspace one project gets, the boundary every call respects, and
the road every question takes.

Three promises, each pinned from a different side:

  what an LLM may see     a restricted column is not merely hidden in the
                          workspace manifest — it is absent, with everything
                          that joined on it, measured it or selected it
  where a call may look   every `wren` process runs inside the workspace with
                          Wren's home pointed at it, so nothing global and
                          nothing of another project is readable
  how a query may run     one read-only SELECT, planned, dry-run, row-limited,
                          and recorded whichever way it went — including the
                          fourth attempt at a statement that failed three times

The engine itself is optional here: the pure-Python halves run everywhere, and
the planner canary runs only where `wren` is installed.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import REPO_ROOT
from pf.tools import wren
from pf.tools import wren_context as wc
from pf.tools import wren_gate as gate

MANIFEST = {
    "catalog": "g", "schema": "p", "dataSource": "DUCKDB", "layoutVersion": 1,
    "models": [
        {"name": "fct_orders", "tableReference": {"schema": "main_marts", "table": "fct_orders"},
         "primaryKey": "order_id",
         "columns": [
             {"name": "order_id", "type": "VARCHAR", "properties": {"pf.role": "natural_key"}},
             {"name": "customer_id", "type": "VARCHAR", "properties": {"pf.role": "foreign_key"}},
             {"name": "amount", "type": "DOUBLE", "properties": {"pf.role": "money_amount"}},
             {"name": "email", "type": "VARCHAR", "isHidden": True, "properties": {"pf.role": "pii_email", "pf.pii": "true"}},
             {"name": "unit_cost", "type": "DOUBLE", "properties": {"pf.role": "unit_price"}},
         ]},
        {"name": "dim_customers", "tableReference": {"schema": "main_marts", "table": "dim_customers"},
         "primaryKey": "customer_id",
         "columns": [
             {"name": "customer_id", "type": "VARCHAR", "properties": {"pf.role": "natural_key"}},
             {"name": "email", "type": "VARCHAR", "isHidden": True, "properties": {"pf.role": "pii_email"}},
             {"name": "phone", "type": "VARCHAR", "properties": {"pf.role": "contact"}},
         ]},
    ],
    "relationships": [
        {"name": "orders_customer", "models": ["fct_orders", "dim_customers"], "joinType": "MANY_TO_ONE",
         "condition": "fct_orders.customer_id = dim_customers.customer_id"},
        {"name": "orders_email", "models": ["fct_orders", "dim_customers"], "joinType": "MANY_TO_ONE",
         "condition": "fct_orders.email = dim_customers.email"},
    ],
    "views": [
        {"name": "v_amounts", "statement": "select order_id, amount from fct_orders"},
        {"name": "v_emails", "statement": "select order_id, email from fct_orders"},
    ],
    "cubes": [{"name": "p_core", "baseObject": "fct_orders",
               "measures": [{"name": "revenue", "expression": "sum(amount)", "description": "Money."},
                            {"name": "emails", "expression": "count(distinct email)", "description": ""}],
               "dimensions": [{"name": "customer_id", "type": "VARCHAR"}, {"name": "email", "type": "VARCHAR"}],
               "timeDimensions": []}],
    "enumDefinitions": [{"name": "fct_orders_status", "values": [{"name": "paid", "value": "paid"}]}],
}

GRAPH = {
    "nodes": [
        {"id": "model:fct_orders", "kind": "Model", "name": "fct_orders", "label": "Orders", "props": {}},
        {"id": "metric:revenue", "kind": "Metric", "name": "revenue", "label": "Revenue",
         "props": {"type": "simple", "agg": "sum", "expr": "amount", "unit": "USD", "description": "All the money."}},
        {"id": "policy:no_pii_export", "kind": "Policy", "name": "no_pii_export", "label": "PII never leaves the warehouse",
         "props": {"severity": "block"}},
        {"id": "decision:ADR-0001", "kind": "Decision", "name": "ADR-0001", "label": "Orders are gross", "props": {"status": "accepted"}},
    ],
    "edges": [{"src": "model:fct_orders", "dst": "metric:revenue", "kind": "measures"}],
}


def _project(tmp_path: Path, manifest: dict | None = None) -> tuple[Path, Path]:
    root = tmp_path
    (root / "platform").mkdir()
    d = root / "groups" / "g" / "projects" / "p"
    (d / "mdl").mkdir(parents=True)
    (d / "kg").mkdir()
    (d / "mdl" / "mdl.json").write_text(json.dumps(manifest or MANIFEST))
    (d / "kg" / "graph.json").write_text(json.dumps(GRAPH))
    return root, d


# --------------------------------------------------------------- redaction --
def test_a_restricted_column_is_absent_not_hidden() -> None:
    out, hidden = wc.redact(MANIFEST)
    names = {m["name"]: [c["name"] for c in m["columns"]] for m in out["models"]}
    assert "email" not in names["fct_orders"] and "email" not in names["dim_customers"]
    assert names["fct_orders"] == ["order_id", "customer_id", "amount", "unit_cost"]
    assert hidden == {"fct_orders": ["email"], "dim_customers": ["email"]}
    assert not any(c.get("isHidden") for m in out["models"] for c in m["columns"])


def test_everything_that_read_the_column_goes_with_it() -> None:
    out, _ = wc.redact(MANIFEST)
    assert [r["name"] for r in out["relationships"]] == ["orders_customer"]
    assert [v["name"] for v in out["views"]] == ["v_amounts"]
    cube = out["cubes"][0]
    assert [m["name"] for m in cube["measures"]] == ["revenue"]
    assert [d["name"] for d in cube["dimensions"]] == ["customer_id"]


def test_the_project_may_withhold_more_roles() -> None:
    out, hidden = wc.redact(MANIFEST, hide_roles=("contact",))
    assert hidden["dim_customers"] == ["email", "phone"]
    assert [c["name"] for c in out["models"][1]["columns"]] == ["customer_id"]


def test_the_platform_manifest_is_never_changed() -> None:
    before = json.dumps(MANIFEST, sort_keys=True)
    wc.redact(MANIFEST, hide_roles=("contact",))
    assert json.dumps(MANIFEST, sort_keys=True) == before


# ---------------------------------------------------------------- workspace --
def test_the_workspace_is_generated_from_tracked_inputs_only(tmp_path: Path) -> None:
    root, d = _project(tmp_path)
    b = wc.build(root, "g", "p", d)
    assert set(b.tracked) >= {"wren_project.yml", "knowledge/rules/00-scope.md", "knowledge/rules/10-concepts.md",
                              "knowledge/rules/20-metrics.md", "knowledge/rules/30-governance.md",
                              "knowledge/rules/40-enums.md"}
    assert "schema_version: 2" in b.tracked["wren_project.yml"]
    assert "name: g__p" in b.tracked["wren_project.yml"]
    assert "data_source: duckdb" in b.tracked["wren_project.yml"]
    scope = b.tracked["knowledge/rules/00-scope.md"]
    assert "groups/g/projects/p" in scope and "`fct_orders`" in scope and "`p_core`" in scope
    assert "classified as personal data" in scope
    metrics = b.tracked["knowledge/rules/20-metrics.md"]
    assert "`revenue`" in metrics and "sum(amount)" in metrics and "USD" in metrics
    assert "emails" not in metrics, "a measure over a withheld column is not a measure the LLM is told about"
    gov = b.tracked["knowledge/rules/30-governance.md"]
    assert "no_pii_export" in gov and "ADR-0001" in gov
    assert "`paid`" in b.tracked["knowledge/rules/40-enums.md"]
    assert "unit_price" in b.tracked["knowledge/rules/10-concepts.md"]


def test_the_rules_are_deterministic(tmp_path: Path) -> None:
    root, d = _project(tmp_path)
    assert wc.build(root, "g", "p", d).tracked == wc.build(root, "g", "p", d).tracked


def test_a_group_states_a_rule_once_for_every_sister(tmp_path: Path) -> None:
    root, d = _project(tmp_path)
    rules = root / "groups" / "g" / wc.GROUP_RULES_REL
    rules.mkdir(parents=True)
    (rules / "fiscal-year.md").write_text("# Fiscal year\nStarts in April.\n")
    b = wc.build(root, "g", "p", d)
    assert b.tracked["knowledge/rules/05-group-fiscal-year.md"].startswith("# Fiscal year")


def test_write_removes_what_is_no_longer_generated_and_keeps_a_stewards_own(tmp_path: Path) -> None:
    root, d = _project(tmp_path)
    ws = wc.workspace(d)
    (ws / wc.RULES_REL).mkdir(parents=True)
    (ws / wc.RULES_REL / "99-old.md").write_text("gone\n")
    (ws / wc.RULES_REL / "desk-notes.md").write_text("ours\n")
    changed = wc.write(d, wc.build(root, "g", "p", d))
    assert not (ws / wc.RULES_REL / "99-old.md").exists()
    assert (ws / wc.RULES_REL / "desk-notes.md").read_text() == "ours\n"
    assert (ws / wc.TARGET_REL).is_file() and (ws / wc.PROJECT_FILE).is_file()
    assert (ws / wc.PAIRS_REL).is_dir()
    assert any(p.name == "99-old.md" for p in changed)
    target = json.loads((ws / wc.TARGET_REL).read_text())
    assert not any(c["name"] == "email" for m in target["models"] for c in m["columns"])


def test_check_tells_stale_missing_and_orphaned_apart(tmp_path: Path) -> None:
    root, d = _project(tmp_path)
    wc.refresh(root, "g", "p", d)
    assert wc.check(root, "g", "p", d, plan=False) == []
    ws = wc.workspace(d)
    (ws / wc.RULES_REL / "00-scope.md").write_text("edited\n")
    (ws / wc.RULES_REL / "20-metrics.md").unlink()
    (ws / wc.RULES_REL / "77-orphan.md").write_text("x\n")
    (ws / wc.PAIRS_REL / "bad.md").write_text("no front matter\n")
    problems = wc.check(root, "g", "p", d, plan=False)
    assert any("00-scope.md is stale" in x for x in problems)
    assert any("20-metrics.md is missing" in x for x in problems)
    assert any("77-orphan.md is no longer generated" in x for x in problems)
    assert any("bad.md needs `nl` and `sql`" in x for x in problems)


def test_a_project_with_no_semantic_layer_has_nothing_to_be_stale(tmp_path: Path) -> None:
    root = tmp_path
    d = root / "groups" / "g" / "projects" / "p"
    d.mkdir(parents=True)
    assert wc.check(root, "g", "p", d) == []


def test_pairs_are_read_as_wren_writes_them(tmp_path: Path) -> None:
    _root, d = _project(tmp_path)
    ws = wc.workspace(d)
    (ws / wc.PAIRS_REL).mkdir(parents=True)
    (ws / wc.PAIRS_REL / "revenue-by-day.md").write_text(
        "---\nnl: revenue by day\nsql: select order_date, sum(amount) from fct_orders\n  group by 1\nsource: user\ntags:\n- kpi\n---\n")
    assert wc.pairs(d) == [{"path": "revenue-by-day.md", "nl": "revenue by day",
                            "sql": "select order_date, sum(amount) from fct_orders group by 1"}]


# ----------------------------------------------------------------- boundary --
def test_every_call_runs_inside_the_workspace_and_nowhere_else(tmp_path: Path, monkeypatch) -> None:
    seen: dict = {}

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, cwd=kw.get("cwd"), env=kw.get("env"))
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(wc.subprocess, "run", fake_run)
    _root, d = _project(tmp_path)
    ws = wc.workspace(d)
    wc.recall(d, "revenue", 3)
    assert seen["cmd"][:3] == ["wren", "memory", "recall"]
    assert seen["cwd"] == str(ws)
    assert seen["env"]["WREN_PROJECT_HOME"] == str(ws)
    assert seen["env"]["WREN_HOME"] == str(ws / ".wren")
    assert "--path" in seen["cmd"] and seen["cmd"][seen["cmd"].index("--path") + 1] == str(ws / wc.MEMORY_REL)


# ------------------------------------------------------------------- policy --
@pytest.mark.parametrize("sql", [
    "select 1",
    "SELECT order_id, amount FROM fct_orders WHERE amount > 0 LIMIT 5",
    "with t as (select 1 as a) select a from t",
    "select a from x union all select b from y",
    "select load_date, set_id from fct_orders  -- a comment; with a semicolon",
])
def test_a_read_is_planned(sql: str) -> None:
    assert gate.policy(sql) is None


@pytest.mark.parametrize("sql, why", [
    ("", "empty"),
    ("select 1; select 2", "one statement"),
    ("drop table fct_orders", "only a SELECT"),
    ("insert into fct_orders select 1", "only a SELECT"),
    ("attach 'other.duckdb' as other", "only a SELECT"),
    ("copy fct_orders to 'x.csv'", "only a SELECT"),
    ("pragma database_list", "only a SELECT"),
    ("create table t as select 1", "only a SELECT"),
])
def test_anything_else_is_refused_by_name(sql: str, why: str) -> None:
    reason = gate.policy(sql)
    assert reason and why in reason, reason


# --------------------------------------------------------------- the road --
def _warehouse(tmp_path: Path) -> Path:
    import duckdb

    path = tmp_path / "p.duckdb"
    con = duckdb.connect(str(path))
    con.execute("create schema main_marts")
    con.execute("create table main_marts.fct_orders as select 1 as order_id, 10.0 as amount union all select 2, 5.0")
    con.close()
    return path


def _drive(monkeypatch, tmp_path: Path, planned_ok: bool = True):
    root, d = _project(tmp_path)
    wh = _warehouse(tmp_path)

    def fake_plan(project_dir, sql):
        return ({"ok": True, "sql": sql.replace("fct_orders", "main_marts.fct_orders")} if planned_ok
                else {"ok": False, "reason": "plan_failed", "message": "table 'nope' not found"})

    monkeypatch.setattr(wren, "plan", fake_plan)
    from pf.runtime.warehouse import Warehouse

    monkeypatch.setattr(Warehouse, "for_project", classmethod(lambda cls, *_a, **_k: SimpleNamespace(path=wh)))
    return root, d


def _ledger(root: Path) -> list[dict]:
    p = root / "groups" / "g" / "loop-ledger.json"
    return json.loads(p.read_text()) if p.exists() else []


def test_a_question_is_planned_dry_run_executed_and_recorded(tmp_path: Path, monkeypatch) -> None:
    root, d = _drive(monkeypatch, tmp_path)
    out = gate.ask(d, "g", "p", "select order_id, amount from fct_orders order by 1", limit=1, root=root)
    assert out.ok and out.stage == "done"
    assert out.columns == ["order_id", "amount"] and out.rows == [{"order_id": 1, "amount": 10.0}], "row-limited"
    assert out.planned_sql.startswith("select order_id, amount from main_marts.fct_orders")
    entries = _ledger(root)
    assert len(entries) == 1 and entries[0]["loop"] == gate.LOOP and entries[0]["outcome"] == "ok"
    assert entries[0]["run_id"] == out.run_id and entries[0]["message"].endswith("rows=1")


def test_a_refusal_is_recorded_too(tmp_path: Path, monkeypatch) -> None:
    root, d = _drive(monkeypatch, tmp_path)
    out = gate.ask(d, "g", "p", "drop table fct_orders", root=root)
    assert not out.ok and out.stage == "policy" and out.rows == []
    (entry,) = _ledger(root)
    assert entry["outcome"] == "gate_blocked" and entry["findings"] == ["policy: only a SELECT is planned; this is DROP"]


def test_a_plan_that_fails_never_reaches_the_warehouse(tmp_path: Path, monkeypatch) -> None:
    root, d = _drive(monkeypatch, tmp_path, planned_ok=False)
    out = gate.ask(d, "g", "p", "select nope from fct_orders", root=root)
    assert out.stage == "plan" and "not found" in out.message and out.planned_sql == ""
    assert _ledger(root)[0]["outcome"] == "gate_blocked"


def test_the_dry_run_catches_what_the_planner_cannot(tmp_path: Path, monkeypatch) -> None:
    root, d = _drive(monkeypatch, tmp_path)
    monkeypatch.setattr(wren, "plan", lambda _d, sql: {"ok": True, "sql": "select * from main_marts.missing"})
    out = gate.ask(d, "g", "p", "select * from fct_orders", root=root)
    assert out.stage == "dry_run" and "missing" in out.message
    assert _ledger(root)[0]["outcome"] == "gate_blocked"


def test_the_fourth_attempt_at_a_failed_statement_is_refused_with_escalate(tmp_path: Path, monkeypatch) -> None:
    root, d = _drive(monkeypatch, tmp_path)
    for attempt in (1, 2, 3):
        out = gate.ask(d, "g", "p", "DROP TABLE fct_orders", root=root)
        assert out.attempt == attempt and out.stage == "policy"
    out = gate.ask(d, "g", "p", "drop   table fct_orders", root=root)   # same statement, other spacing
    assert out.attempt == 4 and "escalate" in out.message and not out.ok
    assert len(_ledger(root)) == 4
    ok = gate.ask(d, "g", "p", "select order_id from fct_orders", root=root)
    assert ok.ok, "the limit is per statement, not per project"


def test_the_row_limit_is_capped(tmp_path: Path, monkeypatch) -> None:
    root, d = _drive(monkeypatch, tmp_path)
    out = gate.ask(d, "g", "p", "select order_id from fct_orders", limit=10**9, root=root)
    assert out.ok and len(out.rows) == 2


# ------------------------------------------------------------- declaration --
def test_the_mcp_server_it_wires_is_transpile_only() -> None:
    server = wren.CAPABILITY.mcp["wren"]
    assert "--no-connect" in server["args"] and "--no-sync" in server["args"]
    assert server["args"][-4:-2] == ["--project", "mdl/wren"] or "mdl/wren" in server["args"]


def test_the_generated_half_of_the_workspace_is_denied_to_edits() -> None:
    deny = wren.CAPABILITY.gate["denylist"]
    assert "**/mdl/wren/target/**" in deny and "**/mdl/wren/wren_project.yml" in deny


def test_the_tool_claims_the_directory_it_writes() -> None:
    (feature,) = wren.TOOL.features
    assert feature.key == "wren_workspace" and feature.paths == ("mdl/wren/**",)
    from pf import architecture as arch

    assert "wren_workspace" in {f.key for f in arch.features()}


def test_every_command_the_skill_names_is_registered() -> None:
    import typer

    app = typer.Typer()
    wren.register_commands(app)
    (group,) = app.registered_groups
    names = {c.name for c in group.typer_instance.registered_commands}
    assert names >= {"workspace", "check", "context", "rules", "recall", "store", "index",
                     "plan", "query", "serve", "doctor", "mdl"}


def test_the_mcp_tools_are_registered_and_row_limited() -> None:
    from pf.mcp import server

    assert {"wren_context", "wren_query"} <= set(server.TOOLS)
    assert "row-limited" in server.wren_query.__doc__


# ------------------------------------------------------------------ engine --
COMMODITY = REPO_ROOT / "groups" / "commodity" / "projects" / "commodity-india"


@pytest.mark.skipif(shutil.which("wren") is None, reason="wren engine not installed (uv sync --extra wren)")
@pytest.mark.skipif(not (COMMODITY / "mdl" / "mdl.json").is_file(), reason="no committed manifest to plan against")
def test_the_engine_plans_every_model_of_a_real_workspace(tmp_path: Path) -> None:
    """The planner canary `check` runs in CI where the engine exists, run here
    against one project's committed manifest — copied, so nothing of the project
    is written."""
    root = tmp_path
    (root / "platform").mkdir()
    d = root / "groups" / "commodity" / "projects" / "commodity-india"
    (d / "mdl").mkdir(parents=True)
    (d / "mdl" / "mdl.json").write_text((COMMODITY / "mdl" / "mdl.json").read_text())
    wc.refresh(root, "commodity", "commodity-india", d)
    assert wc.check(root, "commodity", "commodity-india", d, plan=True) == []
