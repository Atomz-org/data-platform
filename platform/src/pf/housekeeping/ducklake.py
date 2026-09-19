"""DuckLake housekeeping — executable, because the engine makes it callable.

DuckLake does no background maintenance at all: every dbt model writes new
parquet files and a new snapshot, forever. The engine's answer is a set of
maintenance calls, and this module decides *when* they are worth running and
in *what order* — the order is the part that is easy to get wrong by hand:

    flush_inlined_data     small inserts live inlined in the catalog; write
                           them out as parquet so the merge can see them
    merge_adjacent_files   writes compacted files under a NEW snapshot
    expire_snapshots       makes the pre-merge snapshots (and their files)
                           unreferenced — must run after the merge, or the
                           freshly-merged small files stay pinned a week
    cleanup_old_files      deletes what nothing references — last, always

Every call and its signature is pinned live by the integration test in
`test_housekeeping.py` — run where the ducklake extension can load.

`delete_orphaned_files` is deliberately NOT automated. It removes files in the
DATA_PATH that the catalog does not know about — which is exactly what a
concurrent writer's in-flight files look like. An operator runs it, alone,
with the lake quiet.
"""

from __future__ import annotations

import os

from pf.housekeeping.core import Task

#: Alias the maintenance calls address. Matches nothing in the dbt profile on
#: purpose — housekeeping opens its own connection and never rides dbt's.
CATALOG = "lake"

#: A table split across more files than this is planned for a merge. Eight is
#: where DuckDB's own parallel scan stops benefiting from extra files for the
#: table sizes this platform carries; override per lake, not per run.
FRAGMENT_FILES = int(os.environ.get("PF_HOUSEKEEPING_MERGE_FILES", "8"))


def connect():
    """Open the lake the same way the prod target does: by its metadata."""
    import duckdb

    metadata = os.environ.get("DUCKLAKE_METADATA")
    if not metadata:
        raise RuntimeError(
            "DUCKLAKE_METADATA is not set — housekeeping attaches the same "
            "catalog the prod target names, and refuses to guess it.")
    con = duckdb.connect()
    con.execute(f"ATTACH 'ducklake:{metadata}' AS {CATALOG}")
    return con


def inspect(con) -> tuple[list[dict], list[str]]:
    """Per-table file layout plus snapshot age, straight from the catalog."""
    tables = [
        {"table": r[0], "files": int(r[1] or 0), "bytes": int(r[2] or 0)}
        for r in con.execute(
            f"SELECT table_name, file_count, file_size_bytes "
            f"FROM ducklake_table_info('{CATALOG}')").fetchall()
    ]
    snapshots = con.execute(
        f"SELECT count(*), min(snapshot_time) "
        f"FROM ducklake_snapshots('{CATALOG}')").fetchone()
    notes = [f"snapshots: {snapshots[0]}, oldest: {snapshots[1]}"]
    for t in tables:
        t["snapshots"] = int(snapshots[0] or 0)
    return tables, notes


def plan(tables: list[dict], days: int) -> list[Task]:
    """The maintenance worth running now, in the only safe order."""
    tasks: list[Task] = [Task(
        name="flush_inlined_data",
        reason="small inserts are inlined into the catalog, not written as "
               "parquet — flush them to files the merge below can compact "
               "(a no-op when nothing is inlined)",
        sql=(f"CALL ducklake_flush_inlined_data('{CATALOG}')",),
    )]
    fragmented = [t["table"] for t in tables if t["files"] > FRAGMENT_FILES]
    if fragmented:
        tasks.append(Task(
            name="merge_adjacent_files",
            reason=(f"{len(fragmented)} table(s) over {FRAGMENT_FILES} files "
                    f"({', '.join(sorted(fragmented)[:5])}…)" if len(fragmented) > 5
                    else f"{len(fragmented)} table(s) over {FRAGMENT_FILES} files "
                         f"({', '.join(sorted(fragmented))})"),
            sql=(f"CALL ducklake_merge_adjacent_files('{CATALOG}')",),
        ))
    tasks.append(Task(
        name="expire_snapshots",
        reason=f"retention is {days} day(s); every dbt build adds snapshots",
        sql=((f"CALL ducklake_expire_snapshots('{CATALOG}', "
              f"older_than => now() - INTERVAL '{int(days)}' DAY)"),),
    ))
    tasks.append(Task(
        name="cleanup_old_files",
        reason="delete the files the expiry above unreferenced",
        sql=(f"CALL ducklake_cleanup_old_files('{CATALOG}', cleanup_all => true)",),
    ))
    tasks.append(Task(
        name="delete_orphaned_files",
        reason="files in DATA_PATH the catalog does not know about",
        manual=(f"run alone, with no writers on the lake: "
                f"CALL ducklake_delete_orphaned_files('{CATALOG}', "
                f"cleanup_all => true) — a concurrent writer's in-flight "
                f"files are indistinguishable from orphans."),
    ))
    return tasks
