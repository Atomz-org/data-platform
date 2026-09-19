"""Lakehouse housekeeping — the maintenance the engine does not do for you.

An in-warehouse target (Snowflake, BigQuery, ClickHouse) compacts, clusters and
garbage-collects itself; declaring it in `pf.runtime.targets` is the whole job.
The two lakehouse targets are different in a way that bites months later:
every dbt rebuild is a pile of new parquet files and a new snapshot, and
nothing removes the old ones. Query latency then degrades for a reason no
model change explains — the table is fine, its *file layout* is not.

The two engines split the work oppositely, and this module encodes that split
rather than papering over it:

- **DuckLake** hands the platform callable maintenance
  (`ducklake_merge_adjacent_files`, `ducklake_expire_snapshots`,
  `ducklake_cleanup_old_files`) and does nothing on its own. Here,
  housekeeping is *executable*: `pf housekeeping <group> <project> --apply`
  runs the calls in dependency order.

- **Iceberg on Cloudflare R2** is catalog-managed: compaction is R2 Data
  Catalog's job once enabled, snapshot expiry is not offered yet, and the
  DuckDB connection this platform holds has no delete capability. Here,
  housekeeping is *observed*: the same command reports fragmentation and
  snapshot growth per table and says exactly what to enable or run where —
  it never pretends to a capability the connection does not have.

Plan and apply are separate on purpose. Expiring snapshots deletes time
travel, and a platform that does that as a side effect of a status command is
a platform nobody trusts near production. The default is a plan; `--apply`
executes only the tasks the plan marked automated.
"""

from pf.housekeeping.core import Report, Task, detect, plan_for_project, run

__all__ = ["Report", "Task", "detect", "plan_for_project", "run"]
