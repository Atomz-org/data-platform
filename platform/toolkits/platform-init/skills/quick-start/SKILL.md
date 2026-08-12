---
name: quick-start
description: End-to-end from a new data source to a queryable metric in a few prompts. Use when a project is empty or the user says "get started".
---
# Quick start

Ordered workflow. Do not skip steps; each one produces the input for the next.

1. `find-source` (dlt-ingest) — identify the source and scaffold the pipeline.
2. Run the ingest asset; confirm with `list_tables` and `preview_table`.
3. `annotate-source` (dlt-ingest) — attach ontology concept, roles and links.
4. `validate_annotations` — must pass before modelling.
5. `build-staging` (dbt-modeling) — one staging model per raw table.
6. `build-mart` (dbt-modeling) — declare the grain explicitly.
7. `build-semantic-layer` (dbt-semantic) — semantic model + at least one metric.
8. `pf kg build` then `pf kg card` — refresh the graph and the context card.
9. Answer the user's original question with `query_metrics`, not SQL.

Stop after step 4 and show the user the annotation table — it is the cheapest
point to catch a modelling mistake.
