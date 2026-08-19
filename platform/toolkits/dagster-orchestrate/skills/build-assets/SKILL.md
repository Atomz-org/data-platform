---
name: build-assets
description: Add or modify Dagster assets, schedules, sensors and partitions in this platform.
---
<!-- Adapted from dagster-io/skills (vendor/dagster-skills, Apache-2.0) — see registry.yaml. -->
# Dagster in this platform

**Override — this supersedes generic Dagster scaffolding guidance.**

This platform assembles `Definitions` via `pf.runtime.dagster_runtime.build_definitions()`.
**Never** scaffold a `Definitions` object, a resource, an executor, or a pool
in a project. A second `Definitions` silently shadows the factory's resources and
is the most likely way to break this repo.

A project's `definitions.py` is complete as-is:

```python
from pf.runtime.dagster_runtime import build_definitions
defs = build_definitions(group="acme", project="acme-us",
                         source_modules=["acme_us.sources.stripe"])
```

## The pipeline builds itself

You never write Dagster wiring. The factory discovers everything:

| You add | What appears | Action needed |
|---|---|---|
| A `.py` file in `src/<project>/sources/` with `@annotate` resources | One ingest asset per resource | **None** — modules under `sources/` are auto-discovered |
| A dbt model in `transform/models/` | One asset, with dbt's lineage | Re-parse (`pf seed` does it) |
| A dbt source pointing at a dlt table | An edge joining ingest → staging | **None** — the translator maps it |
| A sister to a roll-up's `sisters` map | A cross-location dependency | **None** |

So `definitions.py` never changes after scaffolding. `source_modules=` exists only
as an explicit override for the rare project that must exclude a module.

**Extra assets** go in `src/<project>/defs/` as plain `@asset` functions.

Partitions, schedules, sensors and declarative automation work normally — declare
them on the asset. Always pass `pool=warehouse.writer_pool` on anything that
writes, or you will break sister-project parallelism.

## Lineage

dbt models are emitted through `@dbt_assets`, one asset per model — **never** a
single shelled-out `dbt build`. One opaque asset produces a node with no edges,
which is exactly the failure this avoids.

Ingestion and transformation are joined by the translator in
`pf.runtime.dagster_runtime._translator`: a dbt **source** resolves to the asset
key of the dlt resource that lands it, so `charges` (dlt) → `stg_stripe__charges`
→ `fct_payments` → `fct_revenue` is one continuous graph.

Every asset key is prefixed with the project (`acme_us/fct_revenue`). Sisters have
identically-named models, so without the prefix they collide across code locations.

Cross-project dependencies use `deps=[AssetKey(["<project>", "<asset>"])]`, never
an import — Dagster resolves cross-location dependencies by key alone.

## Three traps in this factory

1. The module lazy-imports dagster **and** uses `from __future__ import annotations`.
   Any dagster type in a signature becomes an unresolvable string and fails with
   NameError. Context params are unannotated.
2. An unannotated `dbt` parameter on `@dbt_assets` is read as an *asset input*,
   not a resource. Use `required_resource_keys={"dbt"}` and
   `context.resources.dbt`.
3. `PF_DUCKDB_PATH` must be set before the manifest loads — `build_definitions`
   sets it from the resolved warehouse path.
