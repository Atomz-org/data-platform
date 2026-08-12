---
name: install-duckdb
description: Install or update DuckDB extensions.
---
# Extensions

The platform pins one extension set for every project: `httpfs`, `json`,
`spatial`, `excel`. They load automatically in `Warehouse.connect`.

```sql
INSTALL spatial; LOAD spatial;
SELECT extension_name, installed, loaded FROM duckdb_extensions();
```

Adding an extension is a **platform** change, not a project one — it affects
every company. Propose it, do not apply it from a project session. Community
extensions need `INSTALL x FROM community;` and an explicit security review.
