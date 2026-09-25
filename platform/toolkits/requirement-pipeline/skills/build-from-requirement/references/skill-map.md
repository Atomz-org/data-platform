# Skill map: which toolkit skill runs where

This skill owns only the order and the spec. Every build step belongs to a
skill in `platform/toolkits/`. For each phase, the table below says who does
the work, what that skill takes from `spec.yaml`, what it hands back, and what
must be true before moving on.

The skills in this table are not optional. A phase done without its owning
skill redoes, badly, what that skill exists to prevent. `validate_spec.py`
prints the same routing per phase (its `SKILLS` table), and
`test_requirement_pipeline_skill.py` fails if either names a skill that is not shipped.

Three kinds of helper appear below:
- **skill**: invoked by name and followed.
- **agent**: a read-only `power-tools` subagent (`sql-reviewer`, `impact-verifier`,
  `semantic-conformance`, `secrets-auditor`). Delegate to it for an
  independent check. It reports and never edits.
- **command**: a user-invoked `power-tools` slash command (`/blast-radius`,
  `/ship`, `/security-audit`, `/performance-audit`). Suggest it; the user runs it.

## Phase 0 — Scope

| Helper | Use when | From the spec → back |
|---|---|---|
| `read-memories` | always, first | `target` → earlier lessons and ADRs for this project |
| `design-architecture` | the project exists | → `kg/architecture.md`: what the project has and what is missing, instead of a file walk |
| `scaffold-project` | the project does not exist | `target` → a governed, bootstrapped project. Stop after it |
| `onboard-project` | the requirement targets an external dbt repo not yet on the platform | repo URL → an adopted project. Then resume here |
| `quality-stack` | `pf tool doctor` shows recce, expectations or elementary unready | → the stack declared and verified |

`quick-start` is this skill's small sibling for "one source, one metric, no
requirement". When a Confluence page exists, this skill governs instead.

## Phase 2 — Extract the spec

| Helper | Use when | From the spec → back |
|---|---|---|
| `answer-with-metrics` | always | each `metrics[]` name and meaning → `list_metrics` / `get_dimensions`. An existing metric is **reused**, and a near miss is a gap reported by name |
| `design-ontology` | a `concepts[]` item has `exists: false` | business noun → class, identity, roles and relations in the right tier |
| `steward-ontology` | data already landed and `pf semantic scan` proposed terms | proposal → approved or remapped axioms. Never approve your own proposal unread |
| `read-file` | the page attaches or links a sample file | sample → column names, types, null rates, key/time/money candidates for `roles` |
| `explore-data` | the source has already landed | raw table → profile for `grain` and `roles`. Profiling only, never a published number |
| `fetch-docs` | a dbt or MetricFlow key on the page needs confirming | → the specific docs page, never a crawl |

## Phase 3 — Blast radius and baseline (existing projects)

| Helper | Use when | From the spec → back |
|---|---|---|
| `recce-review` step 2 | any artefact is `modify` | → `pf tool recce baseline <g> <p>` captured **now**, from the last green build. A baseline taken after the change diffs the change against itself |
| `/blast-radius` · `impact_analysis` | any artefact is `modify` | node → downstream models, metrics, exposure owners |
| `choose-a-test` "before adding any" | a rule adds a test to a hub model | → the dependency count that justifies its runtime |

## Phase 4 — Raw layer (dlt)

| Helper | Use when | From the spec → back |
|---|---|---|
| `find-source` | always for a new source: verified source → OpenAPI → hand-rolled | `sources[].kind`, `connection` → the tier to use |
| `create-rest-pipeline` | `kind: rest_api` | resources, paginator, incremental, `write_disposition` → a module in `sources/` |
| `create-sql-pipeline` | `kind: sql_database` | tables listed explicitly, cursor, reflection level → a module |
| `create-filesystem-pipeline` | `kind: filesystem` | glob, reader, `modification_date` incremental → a module (after `read-file`) |
| `annotate-source` | every resource | `concept`, `grain`, `roles`, `links` → `@annotate`. `validate_annotations` must pass |
| `setup-data-quality` | every resource | → `DEFAULT_CONTRACT`, or `STRICT_CONTRACT` for a source of record. Monitors are generated from roles, never hand-written |
| `steward-ontology` | after the first load | `pf semantic scan … --source <n>` → reviewed proposal |
| `debug-pipeline` | a load failed or left a table empty | → a classification first (feed down, shape changed, contract too strict, cursor wrong), then the fix |
| `optimize-performance` | `schedule.sla` or volume is at risk | → measured bottleneck, then the lever. Never above the writer pool |
| `dignified-python` | any Python written | → code in the house idiom |
| agent `secrets-auditor` | a new source with credentials | → nothing leaked into tracked files |

## Phase 5 — Staging

| Helper | Use when | From the spec → back |
|---|---|---|
| `using-dbt` (staging section) | always | → `pf gen-staging`. Cleaning comes from roles and names from the annotation's `rename` map. Never hand-written |
| `quality-stack` loop steps 2–3, 5 | after staging builds | → the expectations floor derived from roles (`pf tool expectations config`), then run (`pf tool expectations run`) |

## Phase 6 — Intermediate

| Helper | Use when | From the spec → back |
|---|---|---|
| `using-dbt` | every `models.intermediate[]` | inputs, rules → SQL within the layer boundaries |
| `choose-a-test` | every `BR-n` at this layer | `test.type` → the cheapest test that expresses the rule (table below) |
| `add-unit-test` | `test.type: unit_test`, or any window, CASE ladder, dedup or incremental predicate | → failing unit test **first**, then the SQL |
| `add-tests` | `test.type: data_test` | → built-in tests, `error` severity on keys and references |
| `add-expectations` | `test.type: expectation` | → a `dbt_expectations` test, with thresholds in `vars:` |
| `port-snowflake-sql` | `business_rules[].reference_sql.dialect` is not portable | → `pf dialect` report. Ambiguous calls go to a human, never translated |
| agent `sql-reviewer` | after each model is written | → fan-out, grain, null-swallowing joins, incremental predicates, timezones |

### From rule to test (`choose-a-test`)

| The rule is about | `test.type` | Skill |
|---|---|---|
| a key, a reference, a fixed value set | `data_test` | `add-tests` |
| a value's shape (range, type, pattern) | `expectation` | `add-expectations` |
| logic given known inputs | `unit_test` | `add-unit-test` |
| movement against the data's own history | `anomaly_monitor` | `elementary-observe` `add-anomaly-tests` |
| what a metric counts | `metric_filter` | `build-semantic-layer` |
| a column's type or nullability as a promise | `contract` | `contracts-and-access` |

Prefer the cheapest that fits, in the order data_test → expectation → unit_test.
An anomaly monitor is statistical, so it never proves a business rule on its own.

## Phase 7 — Marts

| Helper | Use when | From the spec → back |
|---|---|---|
| `using-dbt` | every `models.marts[]` | → grain in `meta.grain`. No metric policy columns (a mart has no `revenue`) |
| `contracts-and-access` | every mart | → `access: public` and an enforced contract; `private` stays on staging and intermediate |
| `add-tests` | every mart | → grain uniqueness and `relationships` to dimensions |
| `add-expectations` | columns with money, time or percentage roles | → role-derived shape tests plus a row-count floor |
| `add-anomaly-tests` (`elementary-observe`) | the spec names a volume, freshness or share expectation | → `severity: warn` monitors with `timestamp_column` set from the `event_time` role, never on `pii_*` values |
| agent `sql-reviewer` | after each mart is written | → grain verified by query, not assumed |

## Phase 8 — Metrics

| Helper | Use when | From the spec → back |
|---|---|---|
| `build-semantic-layer` | every `metrics[]` not reused | → semantic model, metric, and `saved_query` export for report metrics |
| `answer-with-metrics` | after `pf seed` | → each new metric queried once through `query_metrics`, with its filter stated |
| agent `semantic-conformance` | after the semantic layer changes | → the ontology → annotation → model → metric chain still holds |

## Phase 9 — Build and prove

| Helper | Use when | From the spec → back |
|---|---|---|
| `run-commands` | any dbt invocation outside `pf seed` | → `dbt_build` / `dbt_test` with `+model` or `state:modified+`. Never raw `dbt`, never `--full-refresh` from chat |
| `troubleshoot-runs` | a run or test failed | → a classification (`upstream_data` / `model_logic` / `stale_source` / `test_too_strict`) before the fix |
| `triage-observability` | a monitor or test fired, or before trusting a mart for a report | → recurrence from `main_elementary`, then a classification |
| `triage-alerts` | an Elementary anomaly needs reading | → metric, expected range and actual value, quoted |
| `answer-with-metrics` | each metric-shaped `AC-n` | → the number, with its metric and filter named |
| `query` (`duckdb-ops`) | debugging a failing test's rows | → read-only, truncated evidence. Never used to prove an AC |

## Phase 10 — Orchestration

| Helper | Use when | From the spec → back |
|---|---|---|
| `build-assets` | `schedule` is set | → schedule, sensor or automation condition on the asset in `defs/`, with the writer pool on every write |
| `dignified-python` | always | → code in the house idiom |
| `duckdb-docs` | concurrency questions | → single-writer semantics. Never propose a shared warehouse file |

## Phase 11 — Reporting

| Helper | Use when | From the spec → back |
|---|---|---|
| `build-dashboard` | every `reports[]` page | question, audience, metrics, filters → a page on the standard anatomy |
| `charts-and-diagrams` | every chart, and any mermaid in `trace.md` or the PR | → form first, then colour from the theme. Status colours reserved |
| `dashboard-loop` | after the first draft | → score, critique, fix, repeated until two passes change nothing and `pf report audit` is clean |

## Phase 12 — Catalogue

| Helper | Use when | From the spec → back |
|---|---|---|
| `pf tool openmetadata …` | `catalog` is set | → payload verified, then ingest and publish (`layer-contracts.md` §Catalogue) |
| `design-ontology` "Publishing it" | new terms were added | → `pf tool okf build`, `pf tool okf check`, `pf semantic mdl`: the term reaches every bundle |

## Phase 13 — Close

| Helper | Use when | From the spec → back |
|---|---|---|
| `recce-review` steps 3–6 | any artefact was `modify` | → diff against the Phase 3 baseline, every difference classified as intended (name the `BR-n`), collateral or noise |
| agent `impact-verifier` | any artefact was `modify` | → consumers classified by reading their SQL, not trusting the edge list |
| agent `secrets-auditor` · `/security-audit` | before the first push | → no credential or PII in tracked files or review artefacts |
| `/performance-audit` | the SLA is tight | → measured timings per stage |
| `/ship` | per commit | → gate, conformance, blast radius, diff, one commit (at most 12 files) |
| `pf memory add` | a lesson the next agent would pay for again | → a note in the narrowest module |

## Out of scope: stop and hand back

| The requirement asks for | Why this skill stops | Who owns it |
|---|---|---|
| a dbt upgrade, Fusion, or a warehouse retarget | changes every project, plan-then-apply | `upgrade-and-migrate`, by a human |
| a new DuckDB extension | a platform change affecting every company | `install-duckdb`: propose, do not apply |
| numbers across sister companies | cross-entity reads happen only in `_rollup` | `attach-db` in the roll-up project |
| a control-plane screen | platform UI, not a data product | `forge-ui` |
| a new dbt macro for a foreign dialect | a platform toolkit change with its own probe tests | `port-snowflake-sql` "Adding a macro" |
