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

### `target`
`group`, `project`. When `--project-dir` is given, the validator checks it is
that project.

### `concepts`
`name` (PascalCase ontology class), `exists` (true when found via `kg_search`
or `pf ontology`), `identity` (the natural key in business terms). Any
`exists: false` item routes to `design-ontology` before Phase 4.

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
- `resources[]`:
  - `name` and `endpoint` | `table` | `glob`.
  - `write_disposition`: `append` | `merge` | `replace`. `merge` requires
    `primary_key`.
  - `incremental`: `cursor`, `initial_value`, `lag`.
  - `concept`, `grain`, `roles` {column: role}, `links` {column: Concept}.
    `roles` has exactly one `natural_key`, and every `money_amount` has a
    `currency_code` sibling. These are the same rules `validate_annotations`
    applies, caught one phase earlier.

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
`fct_` / `dim_` / `rpt_`.

### `metrics[]` **(checked)**
`name`, `label`, `description`, `type` (`simple` | `ratio` | `derived` |
`cumulative` | `conversion`), `owner`, `rules`, and by type:
- simple / cumulative: `mart`, `measure: {agg, expr}`, optional `filter`,
  `time_dimension`, `dimensions`
- ratio: `numerator`, `denominator` (metric names, defined here or existing)
- derived: `expr`, `metrics` (names)

A `simple` measure whose `expr` divides is rejected. Make it a ratio.
`agg: average` over a column the spec calls a rate is rejected for the same
reason.

### `reports[]` **(checked)**
`page` (slug), `question` (one per page), `audience`, `metrics` (names),
`grain` (day, week, month), `filters`, `components` (optional hints). Every
metric named must be defined or existing.

### `schedule`
`cron` or `trigger` (`on_source_update`), `timezone`, `partitioning`
(`none` | `daily` | `monthly`), `backfill_from`, `sla` (`"<mart> fresh by HH:MM <tz>"`).

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
