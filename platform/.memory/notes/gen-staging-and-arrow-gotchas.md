---
name: gen-staging-and-arrow-gotchas
description: pf gen-staging drops columns with no annotation role; dlt Arrow loads need add_dlt_load_id/add_dlt_id in .dlt/config.toml
type: project
status: active
---

Two things that cost a seed cycle each on 2026-09-20 (commodity-rollup):

1. `pf gen-staging` writes only the columns named in the resource's `roles` or
   `links`. A raw column with no role is silently absent from `stg_*`, and the
   dbt unit-test fixture then rejects it ("Invalid column name ... Accepted
   columns"). Booleans and secondary dates had no platform role, so the
   commodity group defines `flag` and `reference_date` in
   `ontology/extension.yaml`; `pf_clean` passes unknown roles through.
2. A dlt resource that yields `pyarrow.RecordBatch` lands without
   `_dlt_load_id`/`_dlt_id` unless `.dlt/config.toml` has
   `[normalize.parquet_normalizer] add_dlt_load_id = true / add_dlt_id = true`.
   The generated staging selects `_dlt_load_id`, so the build fails with a
   Binder Error. Adding the config to an existing table fails again ("Adding
   columns with constraints not yet supported") — drop the dataset schema once.

**How to apply:** annotate every column a downstream model needs, and set the
parquet_normalizer keys before the first Arrow load.
