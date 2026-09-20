# Context, loop and graph engineering

How this platform keeps three things small and true as groups and sisters are
added: what an agent has in context, what runs unattended, and what the graph
knows. Each discipline has a platform tier, a group tier and a project tier.
The platform tier is shared, and generated wherever it can be. The group tier
is what a family of sisters decides once. The project tier is one entity. The
worked example throughout is `groups/commodity` and its sister
`commodity-india`, an India landed-price project fed by Yahoo Finance and
gold-api.com.

Two commands sit above all three. `pf bootstrap <g> <p>` re-runs every
generated artefact for one project, and `pf loop audit` scores whether the
result is safe to hand a loop.

## Context engineering

Context is paid on every request for the life of a project, so it is budgeted
and enforced: `pf tokens` fails when a card or a CLAUDE.md is over.

| Tier | What | Written by | Regenerate or check | Budget |
|---|---|---|---|---|
| platform | `CLAUDE.md`, the router | hand | read every session; keep it short | always on |
| platform | `platform/toolkits/ROUTING.md` | hand | `pf tokens` | 400 |
| platform | `docs/VENDOR-CARD.md`, `docs/VENDOR.md` | generated from `platform/src/pf/vendor/registry.yaml` | `pf bootstrap` (vendor docs step) | 800 |
| platform | toolkit skills, `platform/toolkits/<name>/skills/` | hand | `pf loop audit` (plugin marketplace resolves) | on demand |
| group | `groups/commodity/CLAUDE.md` | hand | `pf tokens` | 400 |
| group | `groups/commodity/kg/group_card.md` | generated | `pf bootstrap` (group card step) | 400 |
| group | `groups/commodity/.claude/skills/<name>/SKILL.md` | hand | `claude plugin validate groups/commodity/.claude` | on demand |
| group | `groups/commodity/.claude/.claude-plugin/plugin.json` | scaffold, once | `pf bootstrap` (group plugin + loops step) | none |
| project | `CLAUDE.md` | hand | `pf tokens` | 600 |
| project | `kg/context_card.md` | generated | `pf kg card commodity commodity-india` | 1500 |
| project | `decisions/ADR-*.md` | hand | indexed by `pf kg build` | queried |
| project | `.memory/notes/` | agents, mid-task | promoted by a human, or not | never loaded |

Three layers, by how often a fact is needed. Always on and budgeted: the
router, the group card, the project card and the two CLAUDE.md files. On
demand: skills, loaded when their description matches the task. Queried: the
graph, never loaded.

The group skills are the tier the scaffold used to leave broken. The group
marketplace (`groups/commodity/.claude-plugin/marketplace.json`) lists
`./.claude` as a plugin, and a plugin directory without
`.claude-plugin/plugin.json` is skipped without a message. `pf loop audit`
checks it ("group plugins resolve"), and `pf bootstrap` writes the manifest
where it is missing. Commodity ships three skills: `price-arithmetic` (the
conformed conversion order), `add-a-commodity` (the group half and the sister
half) and `price-feed-triage` (what the feeds do when they fail, and which
loop sees it). They hold what the ontology cannot express and what every
sister must agree on; a sister's own rules stay in its CLAUDE.md.

Loop agents get a different slice. `pf.agents.base.cached_prefix` builds a
byte-stable system prefix from `ROUTING.md`, `loop-constraints.md`, the
project's context card with its generation date stripped, and the group and
project CLAUDE.md rules. Byte-stable matters because the prefix is what the
provider caches: regenerating the card must not bust it, and the contract tier
of `pf evals commodity commodity-india` checks exactly that. With the rules
included the commodity prefix is about 2,900 tokens (4 characters per token,
the estimate `pf evals` prints), above the caching minimum
on Opus 5 (512) and Sonnet 5 (1,024) and below it on Haiku 4.5 (4,096), which
is why the cheapest loops run uncached.

What rolls up: `pf tokens` prints one row per artefact for every group and
project. The README's token table is a snapshot of one project's rows; the
command is the live figure.

```bash
uv run pf tokens
uv run pf kg card commodity commodity-india
claude plugin validate groups/commodity/.claude
```

## Loop engineering

Loops are scheduled, gated, budgeted agent work. The building blocks come from
`vendor/loop-engineering`; the subjects are the platform's own.

| Tier | What | Written by | Run or regenerate |
|---|---|---|---|
| platform | `platform/src/pf/loops/registry.py`: eight loops, each with a level and a budget | hand | `pf loop list` |
| platform | `LOOP.md`, `loop-constraints.md`, `loop-budget.md`, `gate.yaml` | hand | `pf loop audit` |
| group | `groups/commodity/loops.yaml`: cadence, budget, autonomy, waivers | hand | `pf loop list --group commodity` |
| project | `evals/cases/*.json`: the judgements a loop must get right here | hand | `pf evals commodity commodity-india` |
| project | a `### commodity/commodity-india · loops` section in `STATE.md`, while findings or a tripped loop are open | generated | `pf loop run-all commodity commodity-india` |
| project | a `### commodity/commodity-india · onboarding` section in `STATE.md` | generated | `pf align status commodity commodity-india --state` |
| repo | `loop-ledger.json`, append-only | `pf loop` | `pf loop status`, `pf loop reset` |

The eight loops: `freshness-triage`, `test-failure-triage`,
`metric-gap-harvester`, `impact-sentinel`, `dashboard-coverage`, `pii-audit`
and `vendor-drift` at L1 (report only), and `index-refresher` at L2 (patches
inside `gate.yaml`).

A group overrides the registry, never the other way round. `loops.yaml` may
turn a loop off with a reason, change its cadence or budget, lower the
autonomy of a loop that does not write, and waive findings by node name or
glob (`model.column` for `pii-audit`). Raising autonomy is refused: a level is
earned in the ledger and granted in `LOOP.md`. Lowering a writing loop is
refused too: L1 means writes nothing, and a lowered `index-refresher` would
still rebuild the graph, now inside the sweep `pf loop run-all` runs as
read-only. A waiver without a reason is refused for the same reason a silent
override anywhere else is.

Commodity's file makes three decisions. `freshness-triage` runs daily after the
US futures close, because every feed is a daily candle and a two-hourly pass
re-reads the same day. `metric-gap-harvester` waives the `dim_*` tables (a
dimension describes what the facts measure), the `rpt_*` boards and the two
restatement facts, `fct_mcx_lot_equivalents_daily` and
`fct_precious_metal_retail_prices_daily`: a metric on a restated landed price
would restate `avg_landed_price_inr` in another unit, and ADR-0003 says every
mean divides the same way, once. `vendor-drift` is off, because it is
repo-scoped and one report from the platform is enough.

The project tier is where a loop learns the calendar. Two eval cases pin what
`freshness-triage` must say about `futures_prices`: a Monday breach is the
market (no weekend settlement, `futures_weekend_gap_is_market_closure`) and a
Thursday breach is the feed (`futures_midweek_gap_is_a_feed_failure`).

What rolls up: `STATE.md`, one section per project and writer; `loop-ledger.json`;
`pf loop status`; and `pf loop audit`, the readiness score, which includes
whether every group plugin resolves.

```bash
uv run pf loop list --group commodity
uv run pf loop run-all commodity commodity-india
uv run pf loop audit
```

## Graph engineering

The knowledge graph is built, never written. Its inputs are the ontology, the
annotations on each dlt resource, the dbt manifest, the physical warehouse
columns and the semantic manifest. Its outputs are what `kg_search`,
`kg_neighbors`, `kg_path` and `impact_analysis` answer, and the card.

| Tier | What | Written by | Regenerate |
|---|---|---|---|
| platform | `platform/src/pf/ontology/concepts.yaml`: classes, roles, relations, policies | hand | `pf check` |
| platform | node and edge kinds in `pf.kg.store`; every edge runs upstream to downstream | hand | none |
| group | `ontology/instance.yaml` (which platform classes) and `ontology/extension.yaml` (`Commodity`, `PriceObservation`, `FxRate`, `ImportTariff`, the `unit_price` role) | hand | `pf check` |
| group | `shared/transform/` seeds and macros (`units_of_measure`, `to_major_currency`, `reprice_per_unit`) | hand | built in each sister as a local dbt package |
| project | `contracts/annotations.yaml` | generated from `@annotate` | `pf seed` |
| project | `kg/graph.duckdb`, `kg/graph.json` | generated | `pf kg build commodity commodity-india` |
| project | `kg/context_card.md` | generated | `pf kg card commodity commodity-india` |
| project | Decision nodes, one per `decisions/ADR-*.md` | generated | `pf kg build` |

Decisions are in the graph, not beside it. Every `decisions/ADR-*.md` becomes
a node of kind `Decision`, joined by a `decides` edge to what it governs and
found by `kg_search`. An impact report ends with "Decisions to re-read", and
the card carries a "Decisions" line and an "Intermediate models" line, so the
models that do the arithmetic are as visible as the marts that publish it.

Commodity-india's graph has three sources, four raw tables, four staging
models, two intermediate models, eight marts, sixteen metrics and one exposure
(`commodity_price_board`). The blast radius of `int_commodity_prices__usd`
covers every landed price, MCX equivalent, retail price and price metric
downstream of the one model that converts cents, which is the argument for
keeping that conversion in one place.

What rolls up: `pf loop audit` scores "knowledge graph built" and "context
cards generated" across every project, `pf pr report` writes the blast radius
of a change to `data/pr/<n>.json`, and the control plane (`pf ui`) shows the
same verdict CI computed.

```bash
uv run pf kg build commodity commodity-india
uv run pf impact commodity commodity-india model:int_commodity_prices__usd
uv run pf check
```

## The layer contract

dlt extracts. dbt transforms. The line between them is the raw dataset, and
nothing crosses it in the wrong direction.

| Layer | Lives in | Written by | Owns | Never |
|---|---|---|---|---|
| raw | one dlt dataset per source: `reference`, `yahoo_finance`, `gold_api` | dlt Core, from `src/commodity_india/sources/*.py` | the quote as the exchange states it; `DEFAULT_CONTRACT` freezes types; `run_source` reads `rows` back | a transformation, a join, a currency or unit conversion |
| staging | `transform/models/staging/<source>/stg_<source>__<table>.sql` | `pf gen-staging`, from `contracts/annotations.yaml` | one view per raw table, role-driven cleaning; `unit_price` passes through at full precision | a join, a hand edit |
| intermediate | `transform/models/intermediate/` | hand | joins and conversion: `int_commodity_prices__usd` is the only model that turns cents into dollars; `int_fx_rates__daily` gives every calendar day a fix | a metric |
| marts | `transform/models/marts/core/`, `marts/india/` | hand | the grain (`meta.grain`), tests and exposures; `fct_india_landed_prices_daily` reprices to the market unit, applies USD/INR and the duty, once | the arithmetic staging or intermediate already did |
| semantic | `transform/models/semantic/*.yml` | hand | MetricFlow semantic models, metrics and dimensions; every mean a ratio (ADR-0003) | a query against raw or staging |
| reporting | `reporting/` (Evidence) | generated by `pf bootstrap` | a projection of the metrics | a number the semantic layer does not define |

Why the split exists is recorded in
`groups/commodity/projects/commodity-india/decisions/ADR-0004-dlt-core-lands-the-raw-stage.md`.
The dltHub AI Workbench, the reference for agent-built ingestion, writes a
star schema straight from raw through `@dlt.hub.transformation`. That needs
the proprietary `dlthub` package, and its licence limits every use, including
running generated code, to dltHub Services, which excludes Dagster. The
platform already had a staging layer, and a dozen modules (the graph, Dagster
lineage, the MDL projection, the card, the onboarding ladder, the evals) key
on staging being dbt `stg_` models. So dlt Core does the extraction and lands
the raw stage, one dataset per source and named after it because that is what
the generated dbt sources read, and dbt owns everything after it. The
workbench's methodology survives through dlt Core's public API: declarative
`rest_api` where the endpoint allows (gold-api), `RESTClient` where it does not
(Yahoo's parallel arrays), cursors per symbol in dlt's own state, contracts,
and row counts read back before anything is built on the load.

Two rules follow, and the commodity group CLAUDE.md carries both: never
transform inside a dlt resource, and never join in staging. The first keeps the
raw stage rebuildable from the feed alone. The second keeps staging generated,
so `pf gen-staging` can run again without losing a hand edit that was never
supposed to be there.

```bash
uv run pf seed commodity commodity-india          # dlt, then dbt, then graph and card
uv run pf gen-staging commodity commodity-india   # staging from the annotations
uv run pf bootstrap commodity commodity-india     # every generated artefact
```
