---
name: upgrade-and-migrate
description: Upgrade dbt Core, migrate to Fusion, or retarget the warehouse. One-time operations.
---
# Migrations

**Upgrade dbt Core.** Bump the pin in `platform/pyproject.toml` once — it applies
to every project. Then `pf check` across all projects before merging. Read the
migration guide for the target minor; the usual breakages are deprecated configs
and changed selector semantics.

**Core to Fusion.** Run `dbtf parse` first and fix what it reports; Fusion's
static analysis is stricter about ambiguous refs and untyped columns.

**Retarget the warehouse** (duckdb → MotherDuck → Snowflake/BigQuery). Only
`platform/runtime/warehouse.py` and the profile template change; models should be
portable if they avoid DuckDB-specific functions. Set `PF_MOTHERDUCK_DB` to switch
a project without touching code.

All three are plan-then-apply operations. Never run them from a chat turn.
