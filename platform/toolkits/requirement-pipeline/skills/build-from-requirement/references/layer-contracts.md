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
  spec names a run the business triggers.
- An SLA is a freshness check on the mart asset, and its failure notifies
  through the group's `notify.yaml`, not through a new channel.
- Partitions only when the spec is period-scoped with a backfill. The
  partition key must match the dlt incremental window and the dbt incremental
  predicate. If they disagree, rows are silently skipped.
- Every write takes `pool=warehouse.writer_pool`.

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
