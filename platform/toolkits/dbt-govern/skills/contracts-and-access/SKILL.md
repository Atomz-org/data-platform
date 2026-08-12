---
name: contracts-and-access
description: Model contracts, groups, access modifiers and versions.
---
# Governance (dbt Core)

Contracts, `groups`, `access` and model `versions` are all Core features — use them.

```yaml
models:
  - name: fct_revenue
    access: public
    group: finance
    config: {contract: {enforced: true}}
    columns:
      - {name: revenue_usd, data_type: decimal(18,2), constraints: [{type: not_null}]}
```

`access: private` on staging and intermediate; `public` only on marts that
something outside the group consumes.

**Mesh caveat:** cross-project `ref` is dbt Cloud only. Here the boundary is the
project itself — sisters do not `ref` each other. Cross-entity data flows through
`_rollup` via ATTACH READ_ONLY. Shared *macros* travel as a dbt package in
`groups/<group>/shared/transform`.

Declare `exposures` for every dashboard, reverse-ETL sync and ML feature. Without
them impact analysis stops at the mart and cannot name an owner.
