# The requirement spec

`requirements/<REQ>/spec.yaml` is the only input every later phase reads. The
template is `assets/spec-template.yaml`, and a filled example is
`assets/spec.example.yaml`. `scripts/validate_spec.py` enforces everything
marked **(checked)** below.

## Extraction rules

1. **Cite, don't compose.** Every leaf you fill from the page gets a sibling
   `from:` naming its section, table and row (`from: "§KPIs row 2"`). A value
   with no source on the page is an open question, not a default.
2. **Unknown is a value.** Write `null` and add an `open_questions` entry. Set
   `blocking: true` when a build step cannot run without it, for example the
   grain of a mart, a metric's filter, or a source's key.
3. **Business words stay business words** in `description` and `label`.
   Identifiers are snake_case **(checked)**.
4. **One fact, one place.** A rule stated twice on the page becomes one
   `BR-n` cited from both sections.
5. **Out of scope is binding.** Items under `requirement.out_of_scope` are not
   built, even if they look easy.

## Blocks

### `requirement`
`id` (`REQ-…`) **(checked)**, `title`, `summary`, `source` (`system`,
`page_id`, `version`, `url`), `owner` (`name`, `email`), `links` (Jira keys),
`out_of_scope`, `status` (`draft` → `confirmed` after Checkpoint 1).

### `target` **(checked)**
`group`, `project`. When `--project-dir` is given, the validator checks it is
that project, and that it exists — unless:
- `create: true` — the project is scaffolded in Phase 0 (`scaffold-project`);
  refused if it already exists.
- `new_group: true` — the group is created too (`pf new-group`); without it a
  missing group is an error, because a new family is a decision.
- `adopt_repo: <url>` — an external dbt repo is adopted first (`onboard-project`).

### `concepts`
`name` (PascalCase ontology class), `exists` (true when found via `kg_search`
or `pf semantic topology`), `identity` (the natural key in business terms).
An `exists: false` item needs `tier` **(checked)**: `group` when any sister
could use the word, `project` only when nobody else will; `platform` is refused
(hand it back). It is designed and published in Phase 2, before any model.

### `group_changes[]` **(checked)**
Everything the build changes above its project: `kind` (`ontology` |
`shared_connector` | `shared_seed` | `shared_macro` | `conformance_exemption` |
`conformed_model` | `tools`), `name`, `why`. Every sister inherits it, so each
is planned, justified and shown at Checkpoint 1. The validator warns when a
new staging source or intermediate model falls under a path the group's
conformance test holds identical and no exemption is declared.

### `sources[]` **(checked)**
- `name`: the dlt source and raw dataset name, snake_case.
- `kind`: `rest_api` | `sql_database` | `filesystem`.
- `connection`: non-secret locators only (`base_url`, `bucket_url`, `schema`),
  plus `secret_ref`, which is the *name* of the secret. A value that looks like a
  credential fails validation.
- `freshness`: `warn_after` / `error_after` as `<n><m|h|d>`. It becomes dbt
  source freshness and routes Phase 7 to `add-anomaly-tests` for
  `freshness_anomalies`.
- `sample`: optional path or URL of a sample file the page attaches. It routes
  Phase 2 to `read-file`, so roles come from a profile rather than column names.
  Never commit the sample itself.
- `client`: optional name of a client library the page points at. It is a
  candidate, not the contract: Phase 4 probes it against the live source
  before anything is built on it, and falls back to the source's own API when
  it no longer answers. Community wrappers of public sites break silently when
  the site moves.
- `resources[]`:
  - `name` and `endpoint` | `table` | `glob`.
  - `write_disposition`: `append` | `merge` | `replace`. `merge` requires
    `primary_key`.
  - `incremental`: `cursor`, `initial_value`, `lag`.
  - `concept`, `grain`, `roles` {column: role}, `links` {column: Concept}.
    `roles` has exactly one `natural_key`, and every `money_amount` has a
    `currency_code` sibling **or** the resource declares `currency: <ISO>`
    (every amount in one currency, no column for it). These are the same
    rules `validate_annotations` applies, caught one phase earlier.
  - `identities`: optional list of what each amount or quantity measures,
    in words a query can check (`"value = price × quantity × lot size"`). A
    column's name says what the source calls it, not what it holds; a
    "value" can be a notional where the page means a premium. Each identity is
    proved on landed rows at Checkpoint 2 and kept as a `BR-n` with a
    `data_test`.

The generated staging model is `stg_<source>__<resource>`. Refer to it by that
name in `inputs`.

### `business_rules[]` **(checked)**
`id` (`BR-n`), `statement` (the page's wording), `layer` (`staging` |
`intermediate` | `mart` | `metric`), `implemented_in` (model or metric names),
and `test`. Choose the type with `choose-a-test`, taking the cheapest that
expresses the rule:

| `test.type` | Proves | Built by |
|---|---|---|
| `data_test` (`name: unique \| not_null \| accepted_values \| relationships \| expression`) | a key, a reference, a fixed set | `add-tests` |
| `expectation` (`name: expect_…`, thresholds via `vars:`) | a value's shape: range, type, pattern | `add-expectations` |
| `unit_test` | logic given fixed inputs: CASE ladders, windows, dedup, incremental predicates | `add-unit-test` |
| `contract` | a column's type or nullability as a promise | `contracts-and-access` |
| `metric_filter` | what a metric counts (layer must be `metric`) | `build-semantic-layer` |
| `anomaly_monitor` | movement against history. Warned: never the only proof of a rule | `add-anomaly-tests` |

A rule with no `implemented_in` or no `test` fails validation. A rule nobody
can check is one nobody will notice breaking.

`reference_sql: {dialect, sql, from}` is optional. It holds SQL pasted on the
page as evidence of intent. A dialect other than `duckdb` / `ansi` / `dbt` is
warned and routed to `port-snowflake-sql` (`pf dialect`). Never copy it into a
model unread, and never translate a function whose semantics differ by dialect.

Layer choice: a rule that filters or reclassifies *records* (exclude test
orders, map status codes) is `intermediate`. A rule about *what a number
counts* (only succeeded payments count as revenue) is `metric`, as a filter, so
the mart keeps every record and other metrics can count differently.
`staging` only for type or format normalisation driven by roles, and that part
is generated.

### `models.intermediate[]` / `models.marts[]` **(checked)**
`name`, `description`, `grain` (required for marts), `concept`, `inputs`
(existing or planned models), `rules` (`BR-n` ids), `materialized`
(optional), and for marts `kind` (`fact` | `dimension` | `report`) and `columns[]`
(`name`, `role`, `description`, `tests`). Naming is checked: `int_<x>__<y>`,
`fct_` / `dim_` / `rpt_`. Marts also take `access` (`protected` by default;
`public` needs `consumed_outside_group: <who>`) and `monitors` (a volume or
share movement the page names, which routes to `add-anomaly-tests`). A mart
with no column roles is warned: recce and the expectations floor derive from them.
A measure over a `unit_price` or `percentage` column is refused for `sum` and
`average`: make a ratio of additive parts.

### `metrics[]` **(checked)**
`name`, `label`, `description`, `type` (`simple` | `ratio` | `derived` |
`cumulative` | `conversion`), `unit`, `owner`, `rules`, and by type:
- simple / cumulative: `mart`, `measure: {agg, expr, non_additive}`, optional
  `filter`, `time_dimension`, `dimensions`
- ratio: `numerator`, `denominator` (metric names, defined here or existing)
- derived: `expr`, `metrics` (names)

A `simple` measure whose `expr` divides is rejected. Make it a ratio.
`agg: average` over a column the spec calls a rate is rejected for the same
reason.

- `unit` **(checked)**: an ISO currency code (`USD`, `EUR`, `INR`) or one of
  `count`, `percent`, `ratio`, `number`, `duration`. It is how the report
  formats the number, so it is required: without it a report guesses, and a
  volume is printed as dollars. A metric over a mart's `money_amount` column
  must carry a currency code.
- `label` **(checked)**: unique across the spec *and* the project's existing
  metrics, case-insensitively. MetricFlow refuses a manifest where two metrics
  share a label, which bites when the same KPI exists at two grains; qualify
  the label with the grain.
- `measure.non_additive: {dimension, window: last | first}` for a level — a
  balance, an inventory, an open position. Summed over days a level is counted
  once per day. A `sum` over a column whose name reads like a level, without
  it, is warned.

### `reports[]` **(checked)**
`page` (slug), `question` (one per page), `audience`, `metrics` (names),
`grain` (day, week, month), `filters`, `components` (optional hints). Every
metric named must be defined or existing.

`per_entity: <dimension>` makes the page a template: one page per entity
(`reporting/pages/<page>/[<dimension>].md`) plus `<page>/index.md` summarising
all of them. Use it when the page says "each X has its own report"; the
entity list comes from the data, so a new entity gets a page without an edit.

### `schedule`
`cron` or `trigger` (`on_source_update`), `timezone`, `partitioning`
(`none` | `daily` | `monthly`), `backfill_from`, `sla` (`"<mart> fresh by HH:MM <tz>"`).

`per_entity` **(checked)**, when the page asks for each entity (a store, a
market, a customer) to be run, paused or resumed on its own:
- `by`: the entity column.
- `catalogue`: the seed or model listing every entity and its codes. The
  loader and dbt read this one list, so what is fetched and what is modelled
  can never disagree. Adding an entity is a row, not code.
- `stagger`: offset between entities' schedules (`3m`), so N jobs do not
  queue on one warehouse writer at the same minute.
- `start_paused`: entities whose schedule is created stopped. After creation
  the orchestrator owns the state; this list does not override it.

### `catalog`
`domain`, `data_product`, `owners`, `tier` (`Tier1`–`Tier5`), `glossary_terms`,
`pii` (column list, which must also carry a `pii_*` role).

### `acceptance[]` **(checked)**
`id` (`AC-n`), `statement`, `check`, which is one of
- `{metric, grain, where, expect: {equals | between | reconciles_to}}`
- `{test: <dbt test name>}`
- `{manual: <who signs off>}`: allowed, but reported as not automated.

At least one AC is required. A requirement with nothing to accept cannot be finished.

### `open_questions[]`
`id` (`Q-n`), `question`, `blocking`, `ask` (who), `answer`, `answer_from`.
The validator exits `2` while any blocking question has no `answer`.
