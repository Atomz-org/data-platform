---
name: attach-db
description: Attach DuckDB databases for querying, including sister-company roll-ups.
---
# Attaching databases

Session state lives in `.duckdb-skills/state.sql` **inside this project**, so an
attach here is invisible to a sister project.

The project's own warehouse is already the default connection — you do not attach it.

**Cross-entity roll-up (the `_rollup` project only):**

```sql
ATTACH '../acme-us/data/acme_us.duckdb' AS us (READ_ONLY);
ATTACH '../acme-eu/data/acme_eu.duckdb' AS eu (READ_ONLY);
SELECT 'US' AS entity, * FROM us.main.fct_revenue
UNION ALL SELECT 'EU', * FROM eu.main.fct_revenue;
```

`READ_ONLY` is mandatory — it is what guarantees a roll-up can never corrupt a
sister, and what lets sisters keep writing while the roll-up reads.

Because sisters share the group ontology, a union across them is safe by
construction: `fct_revenue` has the same grain and semantics in both. If it does
not, the annotation is wrong — fix that, not the SQL.

**Never attach a sister from a non-rollup project.**
