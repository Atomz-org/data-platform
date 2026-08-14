---
when: The data needed does not exist in the warehouse yet.
rules:
  - Annotate a source with ontology roles before writing any dbt model against it.
  - Annotations drive generated staging, currency normalisation and review config — edit the roles, not the generated files.
---

# dlt-ingest

Ingestion is where meaning is attached, and it is much cheaper to attach it here
than to retrofit it across every model downstream. A `natural_key` or
`money_amount` role set at the source propagates into generated staging, currency
handling and review configuration automatically.

A source landed without annotation looks finished and quietly costs that work
several times over later.
