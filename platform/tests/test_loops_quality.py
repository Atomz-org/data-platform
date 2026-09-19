"""The two quality-stack loops: observability triage and the floor refresher.

What must not regress: the triage loop reads Elementary's *history* and ranks
by recurrence (that is its whole advantage over run_results.json), degrades to
silence when the warehouse or the tables are absent, and never mutates
anything; the refresher rewrites only when the graph has actually moved past
the generated floor.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from pf.loops.registry import expectations_refresher, observability_triage
from pf.tools import expectations as ex


def _project(tmp_path: Path) -> Path:
    d = tmp_path / "groups" / "g" / "projects" / "p"
    (d / "transform").mkdir(parents=True)
    (d / "transform" / "dbt_project.yml").write_text("name: demo\n")
    (d / "data").mkdir()
    (d / "kg").mkdir()
    return d


def _seed_history(d: Path, rows: list[tuple]) -> None:
    con = duckdb.connect(str(d / "data" / "p.duckdb"))
    con.execute("CREATE SCHEMA main_elementary")
    con.execute("""
        CREATE TABLE main_elementary.elementary_test_results (
            test_unique_id VARCHAR, table_name VARCHAR, column_name VARCHAR,
            test_name VARCHAR, status VARCHAR, test_results_description VARCHAR,
            detected_at TIMESTAMP)""")
    con.executemany(
        "INSERT INTO main_elementary.elementary_test_results VALUES (?,?,?,?,?,?,?)",
        rows)
    con.close()


# --------------------------------------------------------------- triage ----
def test_triage_reports_latest_failures_with_recurrence(tmp_path, monkeypatch) -> None:
    d = _project(tmp_path)
    _seed_history(d, [
        # A test that failed twice and last failed — the finding.
        ("t.flaky", "orders", "order_total", "column_anomalies", "fail",
         "zero_count spiked", "2026-08-18 01:00"),
        ("t.flaky", "orders", "order_total", "column_anomalies", "fail",
         "zero_count spiked again", "2026-08-19 01:00"),
        # A test that failed once but passes NOW — history, not a finding.
        ("t.healed", "customers", None, "not_null", "fail",
         "was broken", "2026-08-18 01:00"),
        ("t.healed", "customers", None, "not_null", "pass",
         None, "2026-08-19 01:00"),
    ])
    # Deterministic path only — the agent half is someone else's test.
    monkeypatch.setattr("pf.agents.have_credentials", lambda: False)

    findings = observability_triage(tmp_path, "g", "p", run=None)
    assert len(findings) == 1
    assert "orders.order_total" in findings[0]
    assert "2/2 runs bad" in findings[0]
    assert "healed" not in findings[0]


def test_triage_names_the_missing_tables(tmp_path) -> None:
    """An enabled tool whose tables were never built is one command away —
    the loop should say which command rather than reporting silence."""
    d = _project(tmp_path)
    duckdb.connect(str(d / "data" / "p.duckdb")).close()
    findings = observability_triage(tmp_path, "g", "p", run=None)
    assert findings == ["elementary tables missing — `pf tool elementary run g p`"]


def test_triage_is_silent_with_no_warehouse(tmp_path) -> None:
    _project(tmp_path)
    assert observability_triage(tmp_path, "g", "p", run=None) == []


# ------------------------------------------------------------ refresher ----
def test_refresher_regenerates_only_when_the_graph_moved(tmp_path, monkeypatch) -> None:
    import os
    import time

    d = _project(tmp_path)
    monkeypatch.setattr(ex, "_annotated_marts", lambda _d: [
        ex.MartModel(name="fct_orders", grain="one order", key="order_id")])
    ex.write_tests(d)

    graph = d / "kg" / "graph.duckdb"
    graph.write_bytes(b"")
    # Graph older than the floor: nothing to do.
    old = time.time() - 3600
    os.utime(graph, (old, old))
    assert expectations_refresher(tmp_path, "g", "p", run=None) == []

    # Graph moved, and a model left the ontology: the floor follows.
    monkeypatch.setattr(ex, "_annotated_marts", lambda _d: [
        ex.MartModel(name="fct_orders", grain="one order", key="")])
    now = time.time() + 3600
    os.utime(graph, (now, now))
    findings = expectations_refresher(tmp_path, "g", "p", run=None)
    assert len(findings) == 1 and "2 stale removed" in findings[0]
    assert not (ex.tests_dir(d) / "fct_orders__order_id__unique.sql").exists()


def test_refresher_is_silent_without_a_graph(tmp_path) -> None:
    _project(tmp_path)
    assert expectations_refresher(tmp_path, "g", "p", run=None) == []
