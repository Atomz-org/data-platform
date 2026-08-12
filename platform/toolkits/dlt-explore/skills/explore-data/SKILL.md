---
name: explore-data
description: Explore loaded data and build a marimo notebook. Use for profiling, not for answering governed metric questions.
---
# Explore loaded data

Order: `list_tables` → `display_schema` → `preview_table` → aggregate with
`execute_sql_query`.

Everything is read-only and truncated by policy. If a result is capped, aggregate
in SQL rather than asking for more rows.

**Stop and re-route** if the question is actually a business-metric question —
use `query_metrics`. Exploration is for profiling and debugging.

For a shareable artefact, write a marimo notebook to `notebooks/` that reads the
project DuckDB file read-only. Never have a notebook write to the warehouse.
