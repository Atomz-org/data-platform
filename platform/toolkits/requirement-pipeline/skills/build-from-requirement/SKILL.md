---
name: build-from-requirement
description: Turn a business requirement written in Confluence into a governed pipeline end to end — dlt extraction to the raw layer, dbt staging → intermediate → marts, MetricFlow metrics, an Evidence report, Dagster orchestration and OpenMetadata cataloguing — inside a project of a group (scaffolding the project, and the group-tier vocabulary, when the requirement needs them), by routing every layer to the platform toolkit skill that owns it and delivering it in gate-sized commits that pass CI. Use when someone hands over a Confluence page (URL, page id or pasted export) describing a KPI, report, data product or business rule and wants it built, or says "implement this requirement", "build this from the spec", "new data product from Confluence". Domain-agnostic; works for a new project, a new source, a new metric on existing data, or a change to an existing rule.
---
# Build from a requirement

One requirement in, one traceable pipeline out, inside one project of one
group. This skill owns three things: **the spec**, **the order**, and **the
delivery** (commits that pass the gate and CI). Everything else is done by the
toolkit skill that owns that layer; each phase names it and what to hand it.
`references/skill-map.md` holds the full routing, `references/group-and-delivery.md`
the project-in-group lifecycle, the regeneration chain and the CI checklist.

```
Confluence ─► spec.yaml ─► dlt raw ─► stg_ ─► int_ ─► fct_/dim_ ─► metrics ─► Evidence
   (intake)   (contract)     └──────────── Dagster assets, one graph ────────────┘
   group tier (ontology · shared · conformed) ── quality stack · review agents ── OKF · OpenMetadata
                                                   └─► gate-sized commits ─► CI green
```

## The six rules that make it robust

1. **The spec is the contract, not the page.** Confluence prose is extracted
   once into `requirements/<REQ>/spec.yaml`. Every later step reads the spec.
   A fact the page does not state becomes an `open_questions` entry, never a
   guess.
2. **Reuse before build, family first.** Check the semantic layer
   (`answer-with-metrics`), the graph (`kg_search`), and the group tier —
   shared connectors, shared seeds, conformed models, the group's own skills —
   before writing anything. A second definition of `revenue` is a bug even
   when both are correct today.
3. **Delegate, don't improvise.** A layer built without its owning skill
   repeats the mistake that skill exists to prevent. If a phase names a skill,
   invoke it. Where this skill and an owning skill disagree, the owning skill
   wins and the disagreement is reported.
4. **Logic lives in exactly one layer.** Cleaning belongs in staging, and
   staging is generated. Business rules belong in intermediate. Grain belongs in
   marts. Aggregation policy belongs in metrics. Nothing belongs in a page.
5. **Every tier has its owner.** The project is built here. The group tier
   (vocabulary, shared code, conformed paths) changes only through a planned
   `group_changes` entry with its reason, and a sister's files change only
   through their generators. The platform is handed back.
6. **Stop at the checkpoints (★).** They are the cheapest points to catch a
   misread requirement. In Autonomous scope (`AGENTS.md` §0), a checkpoint with
   a blocking open question ends the run with a report.

## Phase 0 — Scope

- `read-memories`, then `design-architecture`: read `kg/context_card.md` and
  `kg/architecture.md` before any file.
- **Read the family.** The group's `CLAUDE.md`, `kg/group_card.md`, the
  group's own skills (`groups/<g>/.claude/skills/`; the validator lists them),
  `shared/python/src` (connectors), `shared/transform/seeds` (catalogues) and
  the conformance test that holds sisters identical. They override a generic
  habit. Never open a sister project's files.
- **New project.** `target.create: true` → `scaffold-project`:
  `uv run pf new-group <g>` only when `target.new_group` is set, then
  `uv run pf new-project <g> <p> --plan`, ★ confirm with the user, then
  `uv run pf new-project <g> <p>`. Exit when `uv run pf check` reports 0 errors.
  Register what the group needs by hand (its entity seed, `group.yaml`
  resources, the roll-up roster) through the group's own skill. An external
  dbt repo not yet adopted → `onboard-project` first.
- `uv run pf tool doctor <g> <p>`. If recce, expectations or elementary is
  unready, run `quality-stack` (tools are enabled per group: `pf tool enable`).
- Out of scope: stop and hand back per `references/skill-map.md` §Out of scope.

## Phase 1 — Intake from Confluence

`references/confluence-intake.md`, in order of preference:

1. Rovo MCP `getConfluencePage`
2. `scripts/confluence_fetch.py`
3. pasted content

The snapshot goes to `requirements/<REQ>/source.md` with page id, version and
URL, and is never edited. A newer page version is a new snapshot and a spec diff.

## Phase 2 — Extract the spec, and publish new vocabulary

Copy `assets/spec-template.yaml` to `requirements/<REQ>/spec.yaml` and fill it
by `references/requirement-spec.md`. Every leaf gets a `from:`.
`assets/spec.example.yaml` is a small single-source example;
`assets/spec.per-entity.example.yaml` a multi-entity exchange feed with a
group-tier change.

- **Metrics:** `answer-with-metrics` (`list_metrics`, `get_dimensions`) for
  every KPI on the page. If it exists, reuse it by name and leave it out of
  `metrics[]`. If it nearly exists, that is a named gap or an open question.
- **Concepts:** `kg_search` and `uv run pf semantic topology` (the platform and
  group tiers together; `pf ontology` shows only the platform tier). A missing
  class gets `exists: false` and a `tier`: `group` when any sister could use the
  word, `project` only when nobody else ever will.
- **Group changes:** anything above the project — a group-tier class, a shared
  connector or seed, a conformance exemption for a source only this entity has
  — is a `group_changes` entry with its `why`. Sisters inherit it.
- **Roles and grain:** profile evidence, don't infer from column names.
  `read-file` for a sample the page attaches, `explore-data` for data already
  landed.
- **Rules:** each `BR-n` gets one layer and a `test.type` chosen by
  `choose-a-test` (table in `references/skill-map.md` §Phase 6). SQL pasted on
  the page goes in `reference_sql` with its `dialect`.
- **Acceptance:** each `AC-n` is executable: a metric at a grain with an
  expectation, or a named test.

```bash
uv run python platform/toolkits/requirement-pipeline/skills/build-from-requirement/scripts/validate_spec.py \
  groups/<g>/projects/<p>/requirements/<REQ>/spec.yaml --project-dir groups/<g>/projects/<p>
```

Exit `0` valid, `1` errors (fix the spec, not the check), `2` blocking questions
open. The output is the plan: each artefact `create` / `reuse` / `modify`
(project, group, raw, staging, models, metrics, pages, orchestration), the
phases to run, the skills each routes to, the group's own skills, and warnings
for conformed paths, unregistered sources and group connectors to reuse.

### ★ Checkpoint 1 — spec review

Show the plan, the group changes and every sister they reach, rules with layer
and test type, metrics (new vs reused), acceptance criteria and open questions.
Build nothing until the user confirms. Record answers under
`open_questions[].answer` with their source, then set `requirement.status: confirmed`.

**Then publish new vocabulary before anything is built on it** (`design-ontology`
§Publishing it): edit `groups/<g>/ontology/extension.yaml`, then
`uv run pf check`, `uv run pf semantic topology`, `uv run pf kg build <g> <p>`,
`uv run pf semantic mdl <g> <p>`, `uv run pf tool okf build <g> <p> --group`, and
for a group change every sister's bundle (`uv run pf tool okf build --all`) and
every map (`uv run pf harness <g>`). Run the group's own tests
(`uv run pytest groups/<g>/shared/python/tests`); no workflow runs them for you.

## Phase 3 — Blast radius and baseline (only if anything is `modify`)

- `impact_analysis` (or `/blast-radius`) for each modified node; name the
  exposure owners who are not the requester.
- `uv run pf tool doctor <g> <p>`, then the **baseline before the change**:
  `uv run pf tool recce baseline <g> <p>` from the current green build. It
  builds `--target base`, which leaves a base manifest behind — re-parse the
  default target before the next `pf kg build`.
- Adding a test to a hub model: `choose-a-test` "before adding any".

## Phase 4 — Raw layer (dlt)

For each resource marked `create`:

- **Probe first.** One live call before any code. A client library the page
  names (`sources[].client`) is a candidate; if it errors or answers HTML, build
  on the source's own interface and keep the library as a fallback
  (`references/layer-contracts.md` §Raw).
- `find-source`: the platform registry, then the **group's shared connectors**,
  then a verified source → OpenAPI → hand-rolled. A reusable connector belongs
  in the registry — hand that back as a platform change. Then the kind's skill:
  `create-rest-pipeline`, `create-sql-pipeline`, or `create-filesystem-pipeline`
  (after `read-file`).
- Incremental loading is the owning skill's mechanism: a cursor per key in
  `resource_state` (REST), a deliberate `initial_value` then a partitioned
  backfill (SQL), `modification_date` (files). A long backfill commits in
  batches and stops on a batch that makes no progress.
- `annotate-source` with the spec's `concept`, `grain`, `roles`, `links` and
  `currency`. `validate_annotations` must pass.
- `setup-data-quality`: `DEFAULT_CONTRACT` first; `STRICT_CONTRACT` for a
  source of record once a load shows the schema stable (record it in an ADR).
- **Register the source in `src/<pkg>/seed.py`** (`run_source` with its
  contract and required/backup flag). `uv run pf seed <g> <p>` runs only that
  script — an unregistered source loads nothing. The validator warns.
- **Per entity** (`schedule.per_entity`): one pipeline per entity into one
  dataset (`source_name=<source>_<entity>`, `dataset=<source>`), driven by the
  catalogue seed the dbt project also reads.
- Secrets by name only (`secrets_update_fragment`). New credentials → agent
  `secrets-auditor`. Python follows `dignified-python`.
- Run `uv run pf seed <g> <p>` and read `rows` back. Red or empty →
  `debug-pipeline` (classify first). Too slow → `optimize-performance`.
- First load of a new source: `uv run pf semantic scan <g> <p> --source <n>` →
  `steward-ontology` (`pf semantic review`, then `pf semantic approve` — a
  group-wide change, so it goes to Checkpoint 2).

### ★ Checkpoint 2 — landed data

Show the annotation table and rows per raw table. Prove each
`resources[].identities` entry on landed rows (one query each): an amount that
measures something other than the page means is caught here or not at all.
Each proved identity becomes a `BR-n` with a `data_test`.

## Phase 5 — Staging (generated)

`uv run pf gen-staging <g> <p>`; after adding a resource or changing an
annotation, `uv run pf gen-staging <g> <p> --overwrite` and review the diff —
it rewrites every generated file (`using-dbt` §Staging). Never hand-written;
a staging rule is an annotation change (`annotate-source`). Source freshness
from `sources[].freshness` is a source-level freshness monitor
(`add-anomaly-tests` in `elementary-observe`: `uv run pf tool elementary run <g> <p>`
the first time, build twice before trusting it). In a group whose conformance
test covers `models/staging`, a source only this entity has needs its
`conformance_exemption` (Phase 2).

## Phase 6 — Intermediate: the business rules

For each `models.intermediate[]`, follow `using-dbt`. Name it
`int_<entity>__<verb>`, one concern per model, `meta.rules` citing its `BR-n`.
In a conformed group, a model under a conformed path changes in every sister
(the group's skill) or lives outside those paths. Tests come first or with the SQL:

| `test.type` | Skill |
|---|---|
| `unit_test` (any window, CASE ladder, dedup or incremental predicate — always) | `add-unit-test`: write the failing test first |
| `data_test` | `add-tests` |
| `expectation` | `add-expectations`, thresholds in `vars:` |
| `contract` | `contracts-and-access` |

`reference_sql` from a non-portable dialect → `port-snowflake-sql` (`pf dialect`).
Build the model (`run-commands`: `dbt_build` with `+<model>`) **before** agent
`sql-reviewer`, which checks grain by query.

## Phase 7 — Marts: the grain

For each `models.marts[]`, follow `using-dbt`:

- `fct_` / `dim_` / `rpt_`, with `meta: {concept, grain, layer: mart,
  requirement: <REQ>}` and **`meta.role` on every column** from the spec — recce's
  value checks and the expectations floor are derived from it.
- `contracts-and-access`: an enforced contract; `access: public` only when
  something outside the group reads it, otherwise `protected`.
- `add-tests`: grain uniqueness and `relationships`. `add-expectations` only for
  what the role floor does not already say.
- Build (`dbt_build +<mart>`), then `uv run pf kg build <g> <p>`, then the
  quality floor: `uv run pf tool expectations config <g> <p>`,
  `uv run pf tool expectations run <g> <p> --strict`,
  `uv run pf tool recce config <g> <p>` (`quality-stack` loop).
- A volume or share movement the spec names (`models.marts[].monitors`) →
  `add-anomaly-tests` (`elementary-observe`), `severity: warn`,
  `timestamp_column` from `event_time`, never on `pii_*` values.
- Agent `sql-reviewer` on the built mart.

## Phase 8 — Metrics (MetricFlow)

`build-semantic-layer` for each metric not reused:

- `agg_time_dimension` from `event_time`; measures from additive roles
  (`money_amount`, `quantity`). A price or percentage is never summed or
  averaged — a ratio of additive parts.
- `ratio` and `derived` compose existing metrics and never recompute them.
- A level (a balance, a position) gets `non_additive_dimension` on its measure.
- `meta: {requirement, owner, unit}` — `unit` from the spec, how every report
  formats the number. Labels unique across the manifest.
- A `saved_query` export for every metric a report reads.
- Build, `uv run pf kg build <g> <p>` and `uv run pf semantic mdl <g> <p>`, then
  query each new metric once (`answer-with-metrics`) and run agent
  `semantic-conformance`.

## Phase 9 — Build and prove it

```bash
uv run pf seed <g> <p>          # runs src/<pkg>/seed.py (loads + dbt build), then graph + card
uv run pf check                  # ontology conformance, blast radius
uv run pf loop run observability-triage <g> <p>
```

- Any other dbt call goes through `run-commands` (`dbt_build`, selectors). Never
  raw `dbt`, never `--full-refresh` from a session.
- A failure → `troubleshoot-runs`. A fired monitor → `triage-observability` /
  `triage-alerts`. Classify first.
- Execute every `AC-n`. Metric criteria go through `answer-with-metrics`
  (`query_metrics`, or `uv run pf ask`), stating metric and filter. `query` is
  for debugging rows, never proof.
- A failing AC is reported as failing. Change the model only if the rule was
  misread, and fix the spec first.

## Phase 10 — Orchestration (Dagster)

`build-assets` governs: ingest assets are discovered from `src/<pkg>/sources/`,
one per resource, and dbt assets from the manifest. Add only what the spec asks
for in `src/<pkg>/defs/`: a schedule, sensor or automation condition; the SLA as
a freshness check; `pool=warehouse.writer_pool` on every write.

With `schedule.per_entity`, an asset factory over the catalogue makes one
ingest asset, one job and one staggered schedule per entity. **Exclude that
source module from discovery** (`source_modules=` lists the others), or the
factory and discovery load the same tables with two dlt states. Each job is the
entity's whole pipeline: load → an executable step that fails on zero rows →
downstream dbt → report build, with steps that need an external server kept
out (`references/layer-contracts.md` §Orchestration).

`uv run pf dagster-workspace` writes the local workspace; prove the location
loads (`dagster definitions validate -w platform/workspace.yaml`), open the job
graph (no node that feeds nothing), launch one job end to end, and pause and
resume one schedule.

## Phase 11 — Reporting (Evidence)

`uv run pf report build <g> <p>` generates the metric pages, `pages/index.md`,
the source queries and the exposures — it **overwrites** those, so hand-written
pages live under `reporting/pages/<topic>/`. Then, because the exposures
changed, `uv run pf kg build <g> <p>` and `uv run pf semantic mdl <g> <p>` again.
For each `reports[]` page:

- `build-dashboard`: question, audience and filters from the spec; numbers only
  from `queries/metrics/`. `reports[].per_entity` → a templated page per entity
  plus a summary `index.md` in the same topic folder.
- `charts-and-diagrams`: form first, colour from the theme; numbers formatted
  from the metric's `unit`, large tiles scaled.
- `dashboard-loop`: score with `uv run pf report audit <g> <p>`, critique, fix;
  stop when there are no errors, two passes change nothing and every KPI has a
  comparison. `npm run build` on Node 20.
- **Look at every page rendered** (`uv run pf report dev <g> <p>`, or a headless
  screenshot of the build). Query errors and unformatted numbers show only there.

## Phase 12 — Catalogue (OKF, OpenMetadata)

```bash
uv run pf semantic mdl <g> <p>
uv run pf tool okf build <g> <p> --group     # after kg + mdl: it reads both
uv run pf tool okf check <g> <p>
uv run pf air coverage
uv run pf tool openmetadata sync <g> <p>
uv run pf tool openmetadata payload <g> <p>   # owners, tier, glossary, metrics present?
uv run pf tool openmetadata ingest <g> <p>    # database pass first, then dbt
uv run pf tool openmetadata publish <g> <p>   # glossary, role tags, metrics
```

`catalog` values reach OpenMetadata through dbt `meta`, never the UI
(`references/layer-contracts.md` §Catalogue, including the known traps). Verify
by reading one mart back from the server. No server or token → a recorded skip.

## Phase 13 — Close the loop and deliver

### ★ Checkpoint 3 — hand-off

- Anything `modify` → `recce-review` steps 3–6: `uv run pf tool recce run <g> <p>`
  against the Phase 3 baseline; classify each difference as intended (cite the
  `BR-n`), collateral or noise. Then agent `impact-verifier`.
- Agent `secrets-auditor` (or `/security-audit`) before the first push.
- `requirements/<REQ>/trace.md` from `validate_spec.py --trace`: every `BR-n`,
  `AC-n`, metric and page mapped to its file, test and result. Diagrams per
  `charts-and-diagrams`.
- A material choice → an ADR in `decisions/`. A lesson →
  `uv run pf memory add groups/<g>/projects/<p> <slug> "<one line>"`.
- **Deliver** (`references/group-and-delivery.md` §Delivery): regenerate in
  order (`pf kg build`, `pf semantic mdl`, OKF, `pf arch <g> <p>` and
  `pf harness <g> <p>` after staging — both count only the git index), then
  plan the commits with `scripts/plan_commits.py` and let the user run `/ship`
  per slice: `git add` the slice, `pf harness`, `git add` the maps it changed,
  commit (≤ 12 files). Then `uv run pf gate --commits origin/main..HEAD` and the
  CI checklist. A gate refusal is final: report it, never `--no-verify`.

Report what was built per layer and tier, what was reused, the AC results, the
review findings, what was skipped and why, the commits, and the questions still open.

## Choosing the phases

The validator's plan decides this. As a guide:

| The requirement is… | Phases |
|---|---|
| a new project in a group | all, starting with scaffolding in 0 |
| a new data product from a new source | all |
| a new metric over data already modelled | 0–3, 8, 9, 11–13 |
| a changed business rule | 0–3, 6–9, 12–13 |
| a new report over existing metrics | 0–2, 11–13 |
| a new source feeding an existing mart | 0–7, 9, 12–13 |
| each entity run, paused and resumed on its own | adds 10 (`schedule.per_entity`) |

## References

- `references/skill-map.md`: every phase's skills, agents and commands, with inputs, outputs and out-of-scope hand-backs
- `references/group-and-delivery.md`: project in a group, the group tier, the regeneration order, commits and CI
- `references/confluence-intake.md`: fetch, snapshot, versioning, reading page structure
- `references/requirement-spec.md`: every spec field and the extraction rules
- `references/layer-contracts.md`: what each layer may contain, naming, the test floor, Dagster and OpenMetadata
- Upstream practice these toolkits adapt, vendored read-only (initialise with
  `git submodule update --init <path>`): `vendor/dlthub-ai-workbench`,
  `vendor/dbt-agent-skills`, `vendor/dagster-skills`, `vendor/evidence-bi`,
  `vendor/openmetadata`, `vendor/recce`
