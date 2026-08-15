# ADR-0003 — What the base/current diff found

**Status:** accepted · **Stage:** `review` · **Date:** 2026-08-15

## What was compared

Two full builds of all 1,662 nodes into one DuckDB file:

- **base** — the project exactly as imported, in the `base` schema.
- **current** — after the ladder's dialect, layer and metrics stages, in `main`.

Both completed green (`PASS=1653 ERROR=0`, including 532 data tests and 3 unit
tests). Every model wrapped in `sf_least` / `sf_greatest` by ADR-0002 was then
compared row-for-row, because those are the only wraps that change semantics.

## Result

**11 of the 13 wrapped models are byte-identical.** The NULL-propagation change
is real but almost never reachable — most call sites already wrap their arguments
in `coalesce`, so there was no NULL to propagate.

### `mega_wide_daily_flash` — 2 rows, last decimal digit

`total_labor_cost` and two columns derived from it move by 1e-13
(`1006.8500000000001` → `1006.85`). Wrapping `greatest(...)` in a
NULL-propagating `CASE` changes the expression tree, and floating-point addition
is not associative. Accepted: no rounding boundary is crossed and the values are
already presented rounded.

### `scr_customer_churn_propensity` — 308 rows, and **not our doing**

`rfm_total_score` moves by ±1 on 308 rows. It is not computed in this model; it
comes from `int_customer_rfm_scores`, which the ladder never touched — the file
is byte-identical to the imported copy, and it still produces **314 different
rows between two builds of the same SQL**.

The cause:

```sql
ntile(5) over (order by days_since_last_order desc) as recency_score
```

`ntile` with no tie-breaker. Customers who share a `days_since_last_order` land
in whichever bucket the engine's row order puts them in, and that order is not
stable across builds. Every downstream consumer inherits it —
`ml_feature_customer_churn`, `rev_etl_crm_customer_sync`,
`wide_customer_summary`, `cmp_loyalty_vs_non_loyalty`, and the churn model above.

## Decision

Accept both diffs. Neither blocks the onboarding: the first is float precision,
the second predates it.

**The `ntile` non-determinism is a real defect and is left open deliberately.**
Fixing it means adding a tie-breaker — `order by days_since_last_order desc,
customer_id` — which changes historical scores for every tied customer. Whether
that is acceptable is a business call about a customer-facing churn score, not a
call the onboarding gets to make.

## Why this is worth writing down

The onboarding was going to be judged on whether the refactor changed any
numbers. It did, on 310 rows — and 308 of them would have been blamed on the
refactor, because that is the change everyone knew about. Only the diff against a
build of the *untouched* SQL separated the two.

Lineage said what could break. The diff said what did, and said it was something
else.
