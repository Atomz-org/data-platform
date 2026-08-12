---
name: fetch-docs
description: Look up dbt documentation efficiently.
---
# Fetching dbt docs

Prefer the local manifest over the internet: `get_model_details` gives compiled
SQL, columns, grain and description without a fetch.

Go to docs.getdbt.com only for syntax you cannot infer (a config key, a macro
signature, an adapter option). Fetch the specific page; do not crawl.

This project is **dbt Core** + **dbt-duckdb** + **MetricFlow CLI**. Ignore
dbt Cloud-only guidance: Semantic Layer API, Discovery API, Jobs API, cross-project
`ref` in Mesh. Their local equivalents are `mf query`, `manifest.json`,
`run_results.json` and per-project isolation.
