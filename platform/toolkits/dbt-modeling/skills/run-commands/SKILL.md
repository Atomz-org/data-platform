---
name: run-commands
description: Execute dbt CLI commands with the right flags and selectors.
---
# Running dbt

Always via `dbt_build` / `dbt_test` / `dbt_list` so the target and DuckDB path
are wired correctly. Raw `dbt` invocations miss `PF_DUCKDB_PATH`.

Selectors that matter:
- `state:modified+` — the changed models and everything downstream. This is the
  CI selector and the input to impact analysis.
- `+model_name` / `model_name+` — upstream / downstream of one model.
- `tag:daily`, `path:models/marts` — scoped runs.
- `--exclude` beats over-broad selection.

Never `--full-refresh` from a chat turn. Destructive and long-running operations
go through `pf plan` → human review → `pf apply`.
