# Tool precedence — check in this order

Four upstream skill sets are merged here and they overlap. Without this order an
agent answers a governed metric question with ad-hoc SQL.

1. **Structure / lineage question** ("where does X come from", "what uses Y",
   "what breaks if I change Z") → `kg_search`, `kg_neighbors`, `kg_path`,
   `impact_analysis`. **Never grep the repo first.**
2. **Business metric question** ("revenue", "churn", "MRR last quarter")
   → `query_metrics` (MetricFlow). If no metric fits, say which definition is
   missing — do not silently fall back to SQL.
3. **Exploratory / ad-hoc** (profiling, one-off counts, debugging a load)
   → `execute_sql_query` / `preview_table`, read-only.
   Never query `staging` when a mart covers the same grain.
4. **Cross-sister-company** → the `_rollup` project only, via ATTACH READ_ONLY.
   Never read a sister project's files.
5. **Data does not exist yet** → `dlt-ingest`.

Raw SQL that recomputes a defined metric is a bug, not a shortcut.

## Always
- Before any schema or model change, run `impact_analysis` and report the blast
  radius, including exposure owners.
- After changing a model, confirm the blast radius empirically → `recce-review`.
  Lineage says what could break; only a diff says what did.
- Every data-returning tool is truncated by policy (schema + <=20 rows + counts).
  If you need more, aggregate in SQL — do not raise the limit.
