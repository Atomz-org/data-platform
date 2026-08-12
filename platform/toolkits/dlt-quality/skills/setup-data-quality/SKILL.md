---
name: setup-data-quality
description: Add schema contracts and statistical monitors to a pipeline.
---
# Data quality

Two layers, and they catch different failures.

**Contracts (deterministic, at load time).**
`DEFAULT_CONTRACT` is `{tables: evolve, columns: evolve, data_type: freeze}` —
resilient to new fields, strict about type drift. Move a mature source to
`STRICT_CONTRACT` once its schema is stable.

**Monitors (statistical, after load).** Generated from ontology roles by
`pf.runtime.dlt_runtime.monitors_for` — do not hand-write them:

| Role | Monitor |
|---|---|
| `event_time` | freshness (max ts vs expected cadence) |
| `money_amount` | sum drift vs trailing 4-week seasonal baseline |
| `status_enum` | category drift, alert on new/vanished values |
| `natural_key` | row-count band |

dbt tests catch nulls and duplicates. Monitors catch "revenue is 30% below the
same weekday last month" — the failure that actually costs money. Add both.
