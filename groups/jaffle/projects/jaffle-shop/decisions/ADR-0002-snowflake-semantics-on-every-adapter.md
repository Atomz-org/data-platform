# ADR-0002 — Snowflake's semantics are the ones we pin, on every adapter

**Status:** accepted · **Stage:** `dialect` · **Date:** 2026-08-15

## Context

The imported repository ran on Snowflake (`target: snowflake-current`) and kept
DuckDB targets alongside it. Here, development is DuckDB and production is
Snowflake, from one set of models.

`pf align evaluate --stage dialect` found 135 call sites across five functions
that **both** adapters resolve and disagree about. They compile everywhere and
return different values, so nothing announces them:

| Function | Sites | The disagreement |
|---|---:|---|
| `date_trunc` | 66 | same on DuckDB and Snowflake; reversed on BigQuery |
| `datediff` | 30 | Snowflake `(part, start, end)`; dbt's macro `(start, end, part)` |
| `least` | 27 | **Snowflake returns NULL if any argument is NULL; DuckDB skips NULLs** |
| `greatest` | 7 | same as `least` |
| `listagg` | 5 | `WITHIN GROUP` ordering syntax differs; unordered is non-deterministic |

## Decision

Every one is wrapped in its `sf_*` macro from `platform/toolkits/dbt-snowflake`,
which pins **Snowflake's** semantics on whichever adapter compiles it.

Snowflake's, not DuckDB's, because Snowflake is where this code has been running
and where its numbers were checked. Development matching production is the point;
production matching development would silently restate every historical figure.

`date_trunc`, `datediff` and `listagg` are behaviour-preserving on both adapters —
those wraps buy portability to a third warehouse and nothing else. **`least` and
`greatest` are not.** On the 34 sites that use them, a NULL argument previously
gave DuckDB the non-NULL value and Snowflake a NULL; now both give NULL.

## Consequences

- 34 sites can change value in development. Most are already NULL-safe
  (`least(coalesce(x, 0), 5)`), but not all — `least(ta.total_customers,
  tb.total_customers)` in `geo_store_cannibalization` is exactly the sparse case
  the difference shows up on.
- This is what the `review` stage is for. Recce diffs base against current, and
  these 34 are the highest-yield checks in it.
- If a site genuinely wants NULL-skipping, `sf_least_ignore_nulls` says so
  explicitly. Reverting to a bare `least(...)` does not — it reads as an
  oversight and the dialect gate will reopen on it.

## Alternatives rejected

**Rewrite the SQL per warehouse.** Two copies of 1,058 models diverge on the
first bug fix.

**Leave them unwrapped.** They compile. That is the problem: the first sign of
trouble would be a number on a dashboard that nobody could reproduce.

**Pin DuckDB's semantics instead.** Cheaper today, and it would change the
meaning of every historical figure this project has already reported.
