---
name: duckdb-docs
description: Search DuckDB and DuckLake documentation.
---
# DuckDB docs

Search duckdb.org/docs for syntax you cannot infer. Highest-value areas for this
platform: `ATTACH` semantics and read-only mode, extensions (`httpfs`, `spatial`,
`excel`), Friendly SQL, the `read_*` family, and concurrency.

**The concurrency page is the one to know.** DuckDB allows a single writer per
database file. That constraint is why this platform gives every project its own
file and every project its own Dagster writer pool — it is what makes sister
companies genuinely parallel. Do not propose a shared file for multiple writers.
