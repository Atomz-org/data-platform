---
name: performance-audit
description: Find the slow parts of the active project — dbt model timing, DuckDB plans, dlt pipeline throughput — and rank fixes by payoff.
disable-model-invocation: "yes"
---

# Performance audit

Scope: `$ARGUMENTS` (a model, a pipeline, `dbt` / `dlt` / `bi`), else the whole
active project. Measure before recommending; a plausible optimisation that
targets the wrong stage is worse than none.

## 1. Where the time actually goes

dbt already recorded it. Read, don't re-run:

```bash
uv run python - <<'PY'
import json, pathlib
rr = pathlib.Path('transform/target/run_results.json')
if not rr.exists():
    print('no run_results.json — run `dbt build` first'); raise SystemExit
res = json.loads(rr.read_text())['results']
for r in sorted(res, key=lambda r: -r['execution_time'])[:15]:
    print(f"{r['execution_time']:8.2f}s  {r['status']:8}  {r['unique_id']}")
PY
```

The top three rows are the audit. Everything below them is noise until those are
addressed.

## 2. Why the slow ones are slow

For each, `get_model_details` (MCP) for the compiled SQL and materialisation,
then get the plan from DuckDB:

```sql
EXPLAIN ANALYZE <the compiled query>
```

via `execute_sql_query`. Look for, in payoff order:
- a **full scan** feeding a join that could have been filtered first,
- a `view` materialisation that is recomputed by several downstream models —
  each consumer pays the whole cost again,
- an **incremental** model with no usable predicate, so every run is a full
  refresh wearing an incremental's name,
- a join whose keys differ in type (silent cast, no index use),
- fanout: a join that multiplies rows before an aggregate that removes them.

Check the grain claim too — `meta.grain` on a mart that is not actually unique at
that grain both misleads readers and hides a duplicate-row cost.

## 3. Ingestion

```bash
uv run python -c "import json,pathlib;print(pathlib.Path('.dlt').exists())"
```

Then `get_local_pipeline_state` (MCP). Look for: full loads where the source
supports incremental, a write disposition of `replace` on a large resource,
per-row normalisation that could be batched, and resources with no primary key
(which forces the loader into the slow path).

## 4. Reporting layer

Evidence queries run at build. A page that issues a broad scan against a mart is
paying dbt's cost again at render time. Prefer a mart that already aggregates.

## 5. Report

For each finding: measured cost now, the change, the expected cost after, and
how to verify. Rank by **seconds saved per unit of risk**, and say plainly when
a fix is not worth making. If a change touches a model, run `/blast-radius` on it
before recommending it — a faster model that breaks four downstream ones is not
an optimisation.

---

## Generic checklist (retained from the source guide)

**Frontend** — lazy load route components, memoise expensive components, debounce
search inputs and API calls, analyse bundle size, CDN for static assets.
**Backend** — database query optimisation, API response times, caching strategy,
memory leaks.
**Process** — set performance budgets, track Core Web Vitals, add alerts for
regressions, monitor query performance continuously.

**Output format** — analysis, implementation plan, and success metrics: how the
improvement will be measured, and how to roll back if it regresses.
