---
name: troubleshoot-runs
description: Diagnose a failed dbt run or a failing test.
---
# Troubleshooting runs

There is no Cloud Jobs API. The equivalents are `run_results.json` (via
`pf.runtime.dbt_runtime.failed_nodes`) and the Dagster run log.

Procedure:
1. `failed_nodes` — get the failing unique_ids and messages. Do not re-run blind.
2. `kg_neighbors` on each failing model — what feeds it, what depends on it.
3. `preview_table` the upstream input; check the failing rows specifically.
4. Classify before fixing: `upstream_data` / `model_logic` / `stale_source` /
   `test_too_strict`. The fix differs completely per class, and "re-run it" is
   only correct for `stale_source`.
5. If the fix touches a column or a model, run `impact_analysis` first.

A test that fails because the test is wrong is a real outcome — say so rather
than contorting the model to satisfy it.
