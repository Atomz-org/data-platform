"""Housekeeping — the invariants that keep it safe near production.

The dangerous parts are all decisions, not connections: which engine a
project's committed profile names, what order the DuckLake calls run in, and
that the Iceberg side never claims an executable capability. All of that is
testable without a lake, so all of it is tested without one.
"""

from __future__ import annotations

import pytest
from pf.housekeeping import Report, detect, run
from pf.housekeeping import ducklake as dl
from pf.housekeeping import iceberg as ib
from pf.runtime.targets import WAREHOUSES
from pf.scaffold.generator import PROJECT_TARGETS, render_profiles


# ---------------------------------------------------------------- detect ----
def test_detect_tells_the_two_duckdb_lakehouses_apart() -> None:
    """Both are `type: duckdb`; the profile's shape is the only signal."""
    for name, expected in (("ducklake", "ducklake"), ("iceberg", "iceberg")):
        text = render_profiles("demo", {**PROJECT_TARGETS, "prod": WAREHOUSES[name].output})
        assert detect(text) == expected, name


def test_detect_refuses_engines_that_housekeep_themselves() -> None:
    text = render_profiles("demo", {**PROJECT_TARGETS, "prod": WAREHOUSES["snowflake"].output})
    assert detect(text) is None
    # The scaffold placeholder is a local DuckDB file — not a lakehouse either.
    assert detect(render_profiles("demo", PROJECT_TARGETS)) is None
    assert detect("not: [valid") is None


# -------------------------------------------------------------- ducklake ----
def test_ducklake_plan_orders_merge_expire_cleanup() -> None:
    """Merge writes a new snapshot; expiry unreferences the pre-merge files;
    cleanup deletes what nothing references. Any other order pins freshly
    merged files for a whole retention window."""
    tables = [{"table": "fct_orders", "files": 40, "bytes": 1_000_000},
              {"table": "dim_customers", "files": 2, "bytes": 50_000}]
    tasks = dl.plan(tables, days=7)
    names = [t.name for t in tasks]
    assert names.index("flush_inlined_data") < names.index("merge_adjacent_files")
    assert names.index("merge_adjacent_files") < names.index("expire_snapshots")
    assert names.index("expire_snapshots") < names.index("cleanup_old_files")


def test_ducklake_merge_only_when_fragmented() -> None:
    compact = [{"table": "dim_customers", "files": 2, "bytes": 50_000}]
    assert "merge_adjacent_files" not in [t.name for t in dl.plan(compact, days=7)]
    fragmented = [{"table": "fct_orders", "files": dl.FRAGMENT_FILES + 1, "bytes": 1}]
    merge = next(t for t in dl.plan(fragmented, days=7) if t.name == "merge_adjacent_files")
    assert "fct_orders" in merge.reason
    assert merge.automated


def test_ducklake_retention_reaches_the_sql() -> None:
    expire = next(t for t in dl.plan([], days=30) if t.name == "expire_snapshots")
    assert "INTERVAL '30' DAY" in expire.sql[0]
    assert "ducklake_expire_snapshots" in expire.sql[0]


def test_ducklake_orphan_deletion_is_never_automated() -> None:
    """A concurrent writer's in-flight files look exactly like orphans; the
    platform must never delete them as a side effect of routine housekeeping."""
    orphans = next(t for t in dl.plan([], days=7) if t.name == "delete_orphaned_files")
    assert not orphans.automated
    assert "no writers" in orphans.manual


# --------------------------------------------------------------- iceberg ----
def test_iceberg_plans_nothing_executable() -> None:
    """The DuckDB connection has no delete rights and compaction is the
    catalog's job — a task with SQL here would fail at runtime, later, in
    production. The plan must be observation and instruction only."""
    tables = [{"table": "analytics.fct_orders", "snapshots": ib.SNAPSHOT_ALERT + 1}]
    tasks = ib.plan(tables, days=7)
    assert tasks and all(not t.automated for t in tasks)
    assert all(t.manual for t in tasks)


def test_iceberg_expiry_task_appears_only_past_the_alert() -> None:
    quiet = [{"table": "analytics.dim_customers", "snapshots": 3}]
    assert "expire_snapshots" not in [t.name for t in ib.plan(quiet, days=7)]
    noisy = [{"table": "analytics.fct_orders", "snapshots": ib.SNAPSHOT_ALERT + 1}]
    names = [t.name for t in ib.plan(noisy, days=7)]
    assert "expire_snapshots" in names
    assert "managed_compaction" in names  # always worth verifying


# ------------------------------------------------------------------- run ----
def test_run_executes_automated_tasks_in_plan_order(monkeypatch) -> None:
    executed: list[str] = []

    class FakeCon:
        def execute(self, sql: str) -> None:
            executed.append(sql)

        def close(self) -> None:
            pass

    monkeypatch.setattr(dl, "connect", lambda: FakeCon())
    tables = [{"table": "fct_orders", "files": 40, "bytes": 1}]
    report = Report(engine="ducklake", group="g", project="p",
                    tasks=tuple(dl.plan(tables, days=7)))
    done = run(report)
    assert done.applied == ("flush_inlined_data", "merge_adjacent_files",
                            "expire_snapshots", "cleanup_old_files")
    assert executed[0].startswith("CALL ducklake_flush_inlined_data")
    assert executed[-1].startswith("CALL ducklake_cleanup_old_files")


# ----------------------------------------------------------- integration ----
def test_ducklake_maintenance_runs_against_a_real_lake(tmp_path, monkeypatch) -> None:
    """The unit tests pin our decisions; this pins DuckLake's API. If the
    extension renames a maintenance call, this is the test that says so —
    everywhere the extension can load at all (it skips offline)."""
    import duckdb

    probe = duckdb.connect()
    try:
        probe.execute("INSTALL ducklake; LOAD ducklake;")
    except duckdb.Error:
        pytest.skip("ducklake extension unavailable (no network, no cache)")
    finally:
        probe.close()

    monkeypatch.setenv("DUCKLAKE_METADATA", str(tmp_path / "hk.ducklake"))
    con = dl.connect()
    try:
        con.execute("CREATE TABLE lake.t AS SELECT range AS i FROM range(100)")
        for _ in range(3):  # three more snapshots, three more small files
            con.execute("INSERT INTO lake.t SELECT range FROM range(10)")
        tables, _notes = dl.inspect(con)
    finally:
        con.close()  # run() opens its own connection; a held file lock blocks it
    assert [t["table"] for t in tables] == ["t"]
    # Small inserts are INLINED into the catalog, not written as parquet —
    # observed live, and the reason flush_inlined_data leads the plan.
    assert tables[0]["files"] >= 1
    assert tables[0]["snapshots"] >= 4

    done = run(Report(engine="ducklake", group="g", project="p",
                      tables=tuple(tables), tasks=tuple(dl.plan(tables, days=0))))
    assert "flush_inlined_data" in done.applied
    assert "expire_snapshots" in done.applied
    assert "cleanup_old_files" in done.applied

    # Retention 0 keeps only the current snapshot: history actually collapsed.
    con = dl.connect()
    try:
        remaining = con.execute(
            f"SELECT count(*) FROM ducklake_snapshots('{dl.CATALOG}')").fetchone()[0]
    finally:
        con.close()
    assert remaining == 1
