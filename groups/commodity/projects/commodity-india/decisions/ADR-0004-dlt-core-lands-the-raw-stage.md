# ADR-0004: dlt Core lands the raw stage; dbt stages it

**Status:** accepted · 2026-09-17

## Context

The dltHub AI Workbench (`vendor/dlthub-ai-workbench`) is the reference for how
an agent should build ingestion with dlt: declarative `rest_api` sources,
incremental loading, contracts, and reading the load back before trusting it.
Two things stop this project from using it as shipped. Its transformation
layer writes a star schema straight from raw through `@dlt.hub.transformation`,
which needs the proprietary `dlthub` package, and its licence limits every use
of the workbench — including running generated code — to dltHub Services, which
excludes Dagster (`platform/src/pf/vendor/registry.yaml`, `licence_review`).

The platform already has a staging layer: dbt views that `pf gen-staging`
generates from `contracts/annotations.yaml`, with role-driven cleaning. A dozen
platform modules (the knowledge graph, Dagster lineage, the MDL projection, the
context card, the onboarding ladder, the evals) depend on staging being dbt.

## Decision

dlt Core (Apache-2.0) does the extraction and lands the **raw stage**: one dlt
dataset per source (`reference`, `yahoo_finance`, `gold_api`), named after the
source because that name is what the generated dbt sources read. dbt stages it
from there, as before. Nothing from the workbench is copied; its methodology is
applied through dlt Core's public API:

- **Declarative where the endpoint allows.** gold-api is a `rest_api` config: a
  `spot_symbols` parent resource resolves `price/{symbol}`, `processing_steps`
  key and unit each row, `response_actions` skip a symbol the feed cannot
  serve. A dependent resource iterates what its parent yields, so the parent
  yields the symbol list as one page.
- **`RESTClient` where it does not.** Yahoo's chart payload is parallel arrays
  with a request window per symbol, which no selector expresses. The dlt client
  owns the session and retries; Python owns the shape.
- **Incremental in dlt's state.** Cursors live per symbol in
  `dlt.current.resource_state()`, not in `dlt.sources.incremental`, whose one
  cursor per resource would give a newly catalogued symbol no history. dlt
  writes that state to the destination and drops the local copy when the
  dataset is gone, so deleting the warehouse rebackfills.
- **Contracts and verification.** `DEFAULT_CONTRACT` freezes data types.
  `run_source` reads row counts back through `pipeline.dataset()`; the seed
  fails when a source of record left a table empty and only warns for the
  gold-api backup feed.

## Consequences

- `dlt` is the only dlt package installed. `dlt[hub]`, `dlthub` and the
  workbench MCP server are not used; the workbench pin stays for reference and
  drift detection.
- The dlt-ingest toolkit gains `create-rest-pipeline` and `debug-pipeline`,
  written against dlt Core and recorded in the vendor registry as ports.
- Staging generation, Dagster lineage (dlt resource → dbt source → `stg_`) and
  the graph are unchanged. A future dlt-written staging layer would need the
  dlt `model` load path (proven on dlt Core 1.30 with DuckDB) and changes in
  every module that keys on `stg_` models; that is a separate decision.
