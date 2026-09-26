---
name: build-from-requirement
description: Turn a business requirement written in Confluence into a governed pipeline end to end — dlt extraction to the raw layer, dbt staging → intermediate → marts, MetricFlow metrics, an Evidence report, Dagster orchestration and OpenMetadata cataloguing — by routing every layer to the platform toolkit skill that owns it. Use when someone hands over a Confluence page (URL, page id or pasted export) describing a KPI, report, data product or business rule and wants it built, or says "implement this requirement", "build this from the spec", "new data product from Confluence". Domain-agnostic; works for a new source, a new metric on existing data, or a change to an existing rule.
---
# Build from a requirement

One requirement in, one traceable pipeline out. This skill owns two things:
**the spec** and **the order**. Everything else is done by the toolkit skill
that owns that layer. Each phase below names that skill and what to hand it.
`references/skill-map.md` holds the full routing: what each skill takes from
the spec, what it returns, and the exit check.

```
Confluence ─► spec.yaml ─► dlt raw ─► stg_ ─► int_ ─► fct_/dim_ ─► metrics ─► Evidence
   (intake)   (contract)     └──────────── Dagster assets, one graph ────────────┘
                              quality stack · review agents · OpenMetadata over all of it
```

## The five rules that make it robust

1. **The spec is the contract, not the page.** Confluence prose is extracted
   once into `requirements/<REQ>/spec.yaml`. Every later step reads the spec.
   A fact the page does not state becomes an `open_questions` entry, never a
   guess.
2. **Reuse before build.** Check the semantic layer (`answer-with-metrics`) and
   the graph (`kg_search`) for every source, model and metric the spec names. A
   second definition of `revenue` is a bug even when both are correct today.
3. **Delegate, don't improvise.** A layer built without its owning skill
   repeats the mistake that skill exists to prevent. If a phase names a skill,
   invoke it.
4. **Logic lives in exactly one layer.** Cleaning belongs in staging, and
   staging is generated. Business rules belong in intermediate. Grain belongs in
   marts. Aggregation policy belongs in metrics. Nothing belongs in a page.
5. **Stop at the checkpoints (★).** They are the cheapest points to catch a
   misread requirement. In Autonomous scope (`AGENTS.md` §0), a checkpoint with
   a blocking open question ends the run with a report.

## Phase 0 — Scope

- `read-memories`, then `design-architecture`: read `kg/context_card.md` and
  `kg/architecture.md` before any file. They say what the project has and what
  it lacks.
- Resolve `group` / `project` (`uv run pf status`). If the project is missing,
  run `scaffold-project` (`pf new-project <g> <p> --plan` first) and stop, as that
  skill says. If the target is an external dbt repo not yet adopted, run
  `onboard-project` first.
- `uv run pf tool doctor <g> <p>`. If recce, expectations or elementary is
  unready, run `quality-stack` before anything is built on top of it.
- Work only in `groups/<g>/projects/<p>/`. Never read a sister project.
- Out of scope: stop and hand back per `references/skill-map.md` §Out of scope.
  That covers warehouse retargets, new extensions, cross-sister numbers and UI.

## Phase 1 — Intake from Confluence

`references/confluence-intake.md`, in order of preference:

1. Rovo MCP `getConfluencePage`
2. `scripts/confluence_fetch.py`
3. pasted content

The snapshot goes to `requirements/<REQ>/source.md` with page id, version and
URL, and is never edited. A newer page version is a new snapshot and a spec diff.

## Phase 2 — Extract the spec

Copy `assets/spec-template.yaml` to `requirements/<REQ>/spec.yaml` and fill it
by `references/requirement-spec.md`. Every leaf gets a `from:`.

- **Metrics:** `answer-with-metrics` (`list_metrics`, `get_dimensions`) for
  every KPI on the page. If it exists, reuse it by name and leave it out of
  `metrics[]`. If it nearly exists, that is a named gap or an open question.
- **Concepts:** look each noun up (`kg_search`, `uv run pf ontology`). Mark
  `exists: false` → `design-ontology` before Phase 4. If data has already
  landed, the proposal goes through `steward-ontology`.
- **Roles and grain:** profile evidence, don't infer from column names.
  `read-file` for a sample the page attaches, `explore-data` for data already
  landed.
- **Rules:** each `BR-n` gets one layer and a `test.type` chosen by
  `choose-a-test` (table in `references/skill-map.md` §Phase 6). SQL pasted on
  the page goes in `reference_sql` with its `dialect`. It is evidence of intent,
  not code to copy.
- **Acceptance:** each `AC-n` is executable: a metric at a grain with an
  expectation, or a named test.

```bash
uv run python platform/toolkits/requirement-pipeline/skills/build-from-requirement/scripts/validate_spec.py \
  groups/<g>/projects/<p>/requirements/<REQ>/spec.yaml --project-dir groups/<g>/projects/<p>
```

Exit `0` means valid. Exit `1` means errors, so fix the spec rather than the
check. Exit `2` means blocking questions remain open. The output is the plan:
each artefact marked `create` / `reuse` / `modify`, the phases to run, and the
skills each phase routes to.

### ★ Checkpoint 1 — spec review

Show the plan, rules with layer and test type, metrics (new vs reused),
acceptance criteria and open questions. Build nothing until the user confirms.
Record answers under `open_questions[].answer` with their source, then set
`requirement.status: confirmed`.

## Phase 3 — Blast radius and baseline (only if anything is `modify`)

- **Baseline first:** `uv run pf tool recce baseline <g> <p>` from the current
  green build (`recce-review` step 2). Taken after the change, it diffs the
  change against itself and always says "no differences".
- `uv run pf impact <g> <p> <node>` (or `/blast-radius`) for each modified node.
  Name the exposure owners who are not the requester.

## Phase 4 — Raw layer (dlt)

For each resource marked `create`:

- **Probe first.** One live call (or one file read, or one query) before any
  pipeline code. A client library the page names (`sources[].client`) is a
  candidate. If it errors, or returns HTML where it promised JSON, build on the
  source's own interface and keep the library as a fallback
  (`references/layer-contracts.md` §Raw).
- `find-source`: verified source → OpenAPI → hand-rolled, stopping at the first
  tier that fits. Then the kind's skill: `create-rest-pipeline`,
  `create-sql-pipeline`, or `create-filesystem-pipeline` (after `read-file`).
  `write_disposition`, `primary_key` and cursor come from the spec.
  A backfill loads in committed batches, and a batch that makes no progress
  stops the load. With `schedule.per_entity`, each entity gets its own pipeline
  (its own cursor) into one dataset, driven by the spec's catalogue.
- `annotate-source` with the spec's `concept`, `grain`, `roles` and `links`.
  `validate_annotations` must pass.
- `setup-data-quality`: at least `DEFAULT_CONTRACT`, and `STRICT_CONTRACT` for
  a source of record. Monitors are generated from roles.
- Secrets by name only (`secrets_update_fragment`). New credentials → agent
  `secrets-auditor`. Any Python follows `dignified-python`.
- Run it with `uv run pf seed <g> <p>`, then read `rows` back. Red or empty →
  `debug-pipeline`, classifying before fixing. Too slow for the SLA →
  `optimize-performance`.
- First load of a new source: `uv run pf semantic scan <g> <p> --source <n>` →
  `steward-ontology`.

### ★ Checkpoint 2 — landed data

Show the annotation table and rows per raw table. A wrong key, grain or
currency costs one query here and a rebuild later.

Prove each `resources[].identities` entry on the landed rows (one query each)
and show the result. An amount that measures something other than the page
means, such as a notional where the page means a premium, is caught here or
not at all. Each proved identity becomes a `BR-n` with a `data_test`.

## Phase 5 — Staging (generated)

`uv run pf gen-staging <g> <p>` (`using-dbt` §Staging). It is never hand-written.
Change the annotation and regenerate. Freshness from `sources[].freshness`
goes on the dbt source. Then derive and run the quality floor:
`uv run pf tool expectations config <g> <p>` and `uv run pf tool expectations run <g> <p>`
(`quality-stack`).

## Phase 6 — Intermediate: the business rules

For each `models.intermediate[]`, follow `using-dbt`. Name it
`int_<entity>__<verb>`, with one concern per model and `meta.rules` citing its
`BR-n`. Tests are written before or with the SQL:

| `test.type` | Skill |
|---|---|
| `unit_test` (any window, CASE ladder, dedup or incremental predicate) | `add-unit-test`: write the failing test first |
| `data_test` | `add-tests` |
| `expectation` | `add-expectations`, thresholds in `vars:` |
| `contract` | `contracts-and-access` |

`reference_sql` from a non-portable dialect → `port-snowflake-sql` (`pf dialect`).
Ambiguous functions go to a human. After each model, run agent `sql-reviewer`.

## Phase 7 — Marts: the grain

For each `models.marts[]`, follow `using-dbt`:

- Use `fct_` / `dim_` / `rpt_`, with `meta: {concept, grain, layer: mart,
  requirement: <REQ>}` and no metric-policy columns.
- `contracts-and-access`: `access: public` and an enforced contract.
- `add-tests`: grain uniqueness and `relationships`.
- `add-expectations`: role-derived shape tests and a row-count floor.
- Where the spec names a volume, freshness or share expectation:
  `add-anomaly-tests` (`elementary-observe`) with `severity: warn`,
  `timestamp_column` from `event_time`, and never on `pii_*` values.
- Then agent `sql-reviewer`, which verifies grain by query.

## Phase 8 — Metrics (MetricFlow)

`build-semantic-layer` for each metric not reused:

- `agg_time_dimension` comes from `event_time`, and measures from
  `money_amount` / `quantity`.
- `ratio` and `derived` compose existing metrics and never recompute them.
- A level (a balance, a position) gets `non_additive_dimension` on its measure,
  so a month is its last day, not the sum of its days.
- Add `meta: {requirement, owner, unit}`: `unit` from the spec, which is how
  every report formats the number. Labels stay unique across the manifest.
- Add a `saved_query` export for every metric a report reads.
- Afterwards, run agent `semantic-conformance`.

## Phase 9 — Build and prove it

```bash
uv run pf seed <g> <p>          # pipelines + dbt build + graph + card
uv run pf check                  # ontology conformance, blast radius
```

- Any other dbt call goes through `run-commands` (`dbt_build`, selectors). Never
  raw `dbt`, never `--full-refresh`.
- A failure → `troubleshoot-runs`. A fired monitor → `triage-observability` /
  `triage-alerts`. Classify first.
- Execute every `AC-n`. Metric criteria go through `answer-with-metrics`
  (`query_metrics`, or `uv run pf ask`), stating metric and filter. Test
  criteria must be green. `query` is for debugging rows, never proof.
- A failing AC is reported as failing. Change the model only if the rule was
  misread, and fix the spec first.

## Phase 10 — Orchestration (Dagster)

`build-assets` governs: assets already exist for every resource and model. From
`schedule`, add the schedule, sensor or automation condition in
`src/<package>/defs/`. Add partitions only if period-scoped. The SLA becomes a
freshness check, and every write takes `pool=warehouse.writer_pool`. Python
follows `dignified-python`. Then run `uv run pf dagster-workspace`; the location must load.

With `schedule.per_entity`, an asset factory over the catalogue makes one
ingest asset, one job and one staggered schedule per entity. Each job runs the
entity's whole pipeline: load → verify landed → downstream dbt → report. Open
the job graph and confirm it has no node that feeds nothing. Launch one
entity's job end to end, and pause and resume one schedule
(`references/layer-contracts.md` §Orchestration).

## Phase 11 — Reporting (Evidence)

`uv run pf report build <g> <p>`, then for each `reports[]` page:

- `build-dashboard`: question, audience and filters come from the spec, and
  numbers come only from `queries/metrics/`.
- `charts-and-diagrams`: form first, colour from the theme.
- `dashboard-loop`: score with `uv run pf report audit <g> <p>`, critique, fix,
  and stop when two passes change nothing. Then `npm run build` on Node 20.
- Every number is formatted from its metric's `unit`. Large tiles are scaled
  to fit.
- `reports[].per_entity` → a templated page per entity plus a summary index.
- **Open every page once rendered**, or screenshot it headlessly, and read it.
  Query errors and unformatted numbers show only there.

## Phase 12 — Catalogue (OpenMetadata)

```bash
uv run pf tool openmetadata sync <g> <p>
uv run pf tool openmetadata payload <g> <p>   # owners, tier, glossary, metrics present?
uv run pf tool openmetadata ingest <g> <p>    # database pass first, then dbt
uv run pf tool openmetadata publish <g> <p>   # glossary, role tags, metrics
```

`catalog` values reach OpenMetadata through dbt `meta`, never the UI
(`references/layer-contracts.md` §Catalogue, including the known traps). Verify
by reading one mart back from the server: lineage, owner, tier, terms. If terms were added, run
`uv run pf tool okf build` and `uv run pf tool okf check` (`design-ontology`
§Publishing it). No server or token means a recorded skip, not a failure.

## Phase 13 — Close the loop

### ★ Checkpoint 3 — hand-off

- Anything `modify` → `recce-review` steps 3–6: `uv run pf tool recce run <g> <p>`
  against the Phase 3 baseline. Classify each difference as intended (cite the
  `BR-n`), collateral or noise. Then agent `impact-verifier`.
- Agent `secrets-auditor` (or `/security-audit`) before the first push.
- `uv run pf kg build <g> <p>`, `uv run pf arch <g> <p>`, `uv run pf harness <g> <p>`.
- `requirements/<REQ>/trace.md` from `validate_spec.py --trace`: every `BR-n`,
  `AC-n`, metric and page mapped to its file, test and result. Draw any diagram
  per `charts-and-diagrams`.
- A material choice (grain, dedup key, rule reading) → an ADR in `decisions/`.
  A lesson → `uv run pf memory add`.
- Commit with `/ship`, at most 12 files each, in pipeline order.

Report what was built per layer, what was reused, the AC results, the review
findings, what was skipped and why, and the questions still open.

## Choosing the phases

The validator's plan decides this. As a guide:

| The requirement is… | Phases |
|---|---|
| a new data product from a new source | all |
| a new metric over data already modelled | 0–3, 8, 9, 11–13 |
| a changed business rule | 0–3, 6–9, 12–13 |
| a new report over existing metrics | 0–2, 11–13 |
| a new source feeding an existing mart | 0–7, 9, 12–13 |
| each entity run, paused and resumed on its own | adds 10 (`schedule.per_entity`) |

## References

- `references/skill-map.md`: every phase's skills, agents and commands, with inputs, outputs and out-of-scope hand-backs
- `references/confluence-intake.md`: fetch, snapshot, versioning, reading page structure
- `references/requirement-spec.md`: every spec field and the extraction rules
- `references/layer-contracts.md`: what each layer may contain, naming, the test floor, Dagster and OpenMetadata
- Upstream practice these toolkits adapt, vendored read-only: `vendor/dlthub-ai-workbench`,
  `vendor/dbt-agent-skills`, `vendor/dagster-skills`, `vendor/evidence-bi`,
  `vendor/openmetadata`, `vendor/recce`
