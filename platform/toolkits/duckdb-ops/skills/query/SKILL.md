---
name: query
description: Run SQL against the project warehouse. Read-only, truncated, and subordinate to the metrics layer.
---
# Querying

Check ROUTING.md first. This skill is **tier 3** — below the knowledge graph and
below `query_metrics`.

Use it for: profiling, one-off counts, debugging a load, inspecting a failing test's rows.
Do not use it for: any question with a defined metric.

DuckDB Friendly SQL that keeps queries short: `SELECT * EXCLUDE (col)`,
`SELECT * REPLACE (x*2 AS x)`, `GROUP BY ALL`, `ORDER BY ALL`, `QUALIFY`,
`COLUMNS('regex')`, list/struct literals, `FROM tbl SELECT ...`.

Results are truncated by policy (schema + <=20 rows). Aggregate rather than
raising the cap. Writes are refused — data changes go through dbt or a Dagster asset.
