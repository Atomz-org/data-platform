# Layer contracts

What each layer is for, and what it must not contain. The platform skills own
the mechanics. This page is the checklist that one requirement is judged against.

| Layer | Lives in | Contains | Never contains | Owning skill |
|---|---|---|---|---|
| raw | dlt dataset named after the source | data as the source sent it, plus `_dlt_*` load columns | renames, filters, joins | `create-*-pipeline`, `annotate-source` |
| staging | `transform/models/staging/<source>/stg_<source>__<resource>.sql` | 1:1 with a raw table: casts, renames, units, PII masking, all generated from roles | joins, business filters, aggregation | `pf gen-staging` |
| intermediate | `transform/models/intermediate/int_<entity>__<verb>.sql` | business rules, dedup, joins, fan-out control, currency conversion | final grain for consumers, BI naming | `using-dbt`, `add-unit-test` |
| marts | `transform/models/marts/<area>/{fct,dim,rpt}_*.sql` | one declared grain, conformed keys, contract, public access | metric-level filters that would hide rows other metrics need | `contracts-and-access`, `add-tests` |
| semantic | `transform/models/semantic/{sem,metrics}_*.yml` | entities, dimensions, measures, metrics, saved queries | SQL recomputing another metric | `build-semantic-layer` |
| report | `reporting/pages/*.md` | layout, filters and components over `queries/metrics/` | arithmetic on metrics beyond re-dividing ratio components | `build-dashboard` |

## Naming

- Sources: `snake_case` of the system (`stripe`, `erp_orders`), because it
  becomes the raw dataset.
- `stg_<source>__<resource>` (double underscore), generated.
- `int_<entity>__<verb-past-tense>`: `int_orders__deduplicated`,
  `int_invoices__converted_to_usd`.
- `fct_<event-plural>` at the event grain, `fct_<entity>_<period>` for a
  periodic snapshot (`fct_inventory_daily`), `dim_<entity-plural>`,
  `rpt_<purpose>` only when a metric cannot express the shape.
- Metrics: `snake_case` nouns (`gross_revenue`, `order_count`,
  `average_order_value`). Label in Title Case, in the business's own words.
- Every model and metric carries `meta.requirement: <REQ>` so the graph can
  answer "what did REQ-123 produce".

## Tests per layer — the floor

Which kind of test a rule needs is `choose-a-test`'s decision (table in
`skill-map.md` §Phase 6). This is the minimum regardless of rules.

| Layer | Minimum |
|---|---|
| source | freshness (from the spec), `not_null` on the key |
| staging | generated from roles: `unique` + `not_null` on `natural_key`, `accepted_values` on `status_enum` |
| intermediate | one test per `BR-n` implemented here; unit test for any window, CASE ladder, dedup or incremental predicate |
| marts | grain uniqueness (`dbt_utils.unique_combination_of_columns` or `unique`), `relationships` to each dim, enforced contract; expectations generated from roles (`quality-stack`) |
| semantic | each metric queried once in Phase 9, and each AC executed |
| report | `pf report audit` and `npm run build` pass |

Severity: key and referential tests are `error`. Anomaly monitors are `warn`
(`elementary-observe`).

## Raw (dlt) — what makes a load survive

The source is the one layer the platform does not control. These hold for any
source kind:

- **Probe before you build.** Call the endpoint (or open the file, or query the
  table) once and read the answer before writing a pipeline around it. A client
  library the page names (`sources[].client`) is tried first and kept as a
  fallback, but if it answers with an error page, an HTML body where JSON was
  promised, or a 403, the source's own interface is the contract. Record which
  route answered in a column (`extracted_via`), so a later change of route is
  visible in the data.
- **Resumable in committed batches.** A backfill of thousands of requests is
  split into batches, each one load with its incremental state. A stopped run
  loses one batch, never the backfill. Every batch must make progress: a batch
  that plans the same work as the one before (an open item re-planned forever)
  stops the load with an error instead of looping.
- **Per-entity state when the job is per entity.** With `schedule.per_entity`,
  each entity runs its own dlt pipeline (`<project>_<source>_<entity>`), so its
  cursor and its failures are its own, into one shared dataset. One entity's
  outage never blocks another's load.
- **Identities before models.** For every amount and quantity, prove what it
  measures on landed rows (`resources[].identities`) and keep the proof as a
  test. A turnover that turns out to be a notional overstates activity by an
  order of magnitude, and nothing downstream will notice.
- **Space requests to a public site** and treat its terms of use as the owner's
  decision, recorded in an ADR, not the pipeline's.

## Portability

The project's warehouse (DuckDB in dev, the prod adapter from the scaffold) is
not the requirement's business. Write dialect-portable SQL with `dbt_utils` or
cross-database macros, and check it with `uv run pf dialect <path>` when unsure. A
dialect-specific function needs a reason in the model description.

## Orchestration (Dagster)

- Assets already exist for every dlt resource and dbt model, prefixed with the
  project (`<project>/fct_orders`). The raw → staging edge is made by the
  translator. Do not reproduce it.
- Schedules, sensors and automation conditions go in `src/<package>/defs/`.
  Prefer declarative automation (`AutomationCondition.eager()` on marts,
  `on_cron` on the ingest assets) over a job per requirement. Use a job only when the
  spec names a run the business triggers, or `schedule.per_entity` asks for
  one per entity.
- **One job per entity** (`schedule.per_entity`) comes from an asset factory
  over the catalogue: one ingest asset per entity, one job and one schedule per
  entity, schedules staggered by `stagger`. Each job is the entity's whole
  pipeline: its load, a step that verifies rows landed, the dbt models
  downstream of the raw tables, and the report build. So a paused entity is
  paused end to end, and a run is never "loaded but not modelled".
- **Only executable assets go in a job.** A table declared as a non-executable
  asset spec (an external asset standing in for a raw table) is dropped from a
  job's selection. The job graph then shows the load feeding nothing. Make
  that node an executable verification step (it reads what landed and fails on
  zero rows) instead.
- **Keep optional external steps out of scheduled jobs.** A step that needs a
  server a developer may not run (a catalogue sync) belongs in its own job.
  Otherwise every scheduled run fails locally for a reason unrelated to the
  data.
- A file of initial schedule states (`start_paused`) only sets the state a
  schedule is *created* in. Once it exists, the orchestrator owns the state,
  and pausing or resuming is an action there, not a file edit.
- An SLA is a freshness check on the mart asset, and its failure notifies
  through the group's `notify.yaml`, not through a new channel.
- Partitions only when the spec is period-scoped with a backfill. The
  partition key must match the dlt incremental window and the dbt incremental
  predicate. If they disagree, rows are silently skipped.
- Every write takes `pool=warehouse.writer_pool`.

## Reporting (Evidence)

- Numbers are formatted from the metric's `unit`: a currency as its symbol, a
  count without one, a percent as a percent. A tile showing a large amount is
  scaled (thousands, millions, billions) by its magnitude, so it fits.
  `pf report audit` is clean before hand-off.
- A per-entity page is a template (`[<dimension>].md`) over the data's own
  entity list, with an index page summarising all entities. Display labels are
  computed in SQL, not in page expressions.
- **Look at the rendered page.** A query error, an empty chart, or an
  unformatted number is visible only when the page renders. Build it, open
  each page (or screenshot it headlessly), and read it before calling Phase 11
  done. A page reading a stale review baseline schema fails the same way:
  rebuild the baseline rather than editing the page.

## Catalogue (OpenMetadata)

The project publishes. Nobody types into the UI.

1. `pf tool doctor <g> <p>` confirms `openmetadata` is enabled and reachable.
   Enable it with `pf tool enable` only if the group has not.
2. Put the spec's `catalog` block into dbt `meta` on each mart and metric:
   `owner`, `meta.openmetadata.tier`, `meta.openmetadata.domain`,
   `meta.openmetadata.glossary` (the upstream dbt-ingestion keys). Then
   **verify** they appear in `pf tool openmetadata payload`. If a key is not
   carried, say so rather than assume it published.
3. `sync`, then `ingest`, which runs the database pass before the dbt pass. The
   dbt pass attaches models, column lineage, tests and owners to tables the
   database pass created.
4. `publish` sends glossary terms (from the ontology), role tags (`PII.Sensitive`
   for `pii_*` roles) and metrics with their expressions.
5. Owners' later edits come back through `pf tool openmetadata pull` as
   `catalog/owner-edits.yaml`, a proposal that lands in a pull request.

The catalogue points at production. Without a production target or a
token, record the skipped steps in `trace.md` and carry on.

Known traps, each cheap to check and expensive to discover:
- On a fresh server, `publish` can fail the first time, because glossary terms
  relate to terms not yet created. Run it a second time. If the second pass
  fails, that is a real error.
- Ingestion workflow files resolve relative artefact paths against the
  ingestion tool's own working directory, not the project. Pass absolute paths
  to `manifest.json` and `catalog.json`.
- Verify by reading back, not by exit code: search the server for one mart,
  open its lineage, and confirm owners, tier and glossary terms arrived.
