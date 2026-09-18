---
name: create-sql-pipeline
description: Ingest from a SQL database (Postgres, MySQL, MSSQL) with dlt.
---
# SQL database pipeline

Use `dlt.sources.sql_database`. Decisions to make explicitly:

- **Table selection** — never `with_resources()` everything. List the tables.
- **Incremental** — pick a monotonic cursor (`updated_at`, or an autoincrement id)
  and set `incremental=dlt.sources.incremental("updated_at")`. Without it every
  run is a full copy.
- **Write disposition** — `merge` with `primary_key` for mutable tables,
  `append` for immutable event tables.
- **Reflection level** — `full` when column types matter downstream;
  `full_with_precision` carries precision some destinations reject.
- **Backfill** — a large first load is a `pf seed` run with a deliberate
  `initial_value`, then a Dagster backfill over partitions; never a bare run
  with no cursor.

Annotate every resource before finishing.
