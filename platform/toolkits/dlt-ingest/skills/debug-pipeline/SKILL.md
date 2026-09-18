---
name: debug-pipeline
description: Diagnose a failed or empty dlt load with dlt Core's own tools — trace, load packages, failed jobs, schema and the dataset API.
---
# Debug a dlt pipeline

Pipelines are named `<project>_<source>` (`pf.runtime.dlt_runtime.build_pipeline`)
and keep their working folder under dlt's default `~/.dlt/pipelines/<name>`.

1. `dlt pipeline <name> info` — state, dataset, last load. Then
   `dlt pipeline <name> trace`: the last run step by step, with timings and the
   exception that stopped it.
2. `dlt pipeline <name> failed-jobs` — each failed load job with its error.
   `dlt pipeline <name> load-package [<load_id>]` — what a package contained.
3. `dlt pipeline <name> schema` — the inferred schema. Compare column types
   with the annotation and the generated dbt source; a `data_type: freeze`
   violation names the column that changed type upstream.
4. Rows, through the same API the seed uses:
   `python -c "import dlt; print(dlt.attach('<name>').dataset().row_counts().fetchall())"`.
   Staging reads exactly these tables, so an empty one here is the whole story.
5. Rebackfill one resource with `dlt pipeline <name> drop <resource>` (its
   tables and state go; the next run reloads it). Deleting `data/<project>.duckdb`
   rebackfills everything: dlt drops local state when the dataset is gone.

Classify before fixing, as `troubleshoot-runs` does for dbt: feed down, shape
changed, contract too strict, or cursor wrong. Never fix a red load by editing
the raw table — fix the source or the contract, then `pf seed`.
