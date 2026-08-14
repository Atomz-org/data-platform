---
when: Profiling, one-off counts, debugging a load — exploratory work only.
rules:
  - Subordinate to the metrics layer; never query raw tables to answer a defined metric.
  - Never query staging when a mart covers the same grain.
  - Read-only, and truncated by policy (schema + <=20 rows + counts) — aggregate in SQL rather than raising the limit.
  - Cross-sister reads happen only in the _rollup project, via ATTACH READ_ONLY.
---

# duckdb-ops

Direct SQL is for questions the semantic layer is not meant to answer: what does
this file look like, why did this load fail, how many rows landed. The moment the
question is about a business quantity, it belongs to `dbt-semantic`.

The truncation is policy, not a limitation to work around. Needing more rows is
almost always a sign the question should have been an aggregate.
