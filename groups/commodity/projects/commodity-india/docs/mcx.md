# MCX bhavcopy — runbook

What MCX settled each session, for every commodity it lists, landed by dlt,
modelled by dbt, reported by Evidence and orchestrated by Dagster. Why it is
built this way: [ADR-0006](../decisions/ADR-0006-mcx-bhavcopy-one-pipeline-per-commodity.md).

```
mcx_<c>_daily ─► mcx_<c>_ingest  (one job per commodity = the whole pipeline)
 (schedule,        ├─ commodity_india/mcx_<c>        dlt: that commodity's pipeline only
  staggered 3 min) ├─ mcx_landed_tables              the 3 raw tables: verify rows landed
                   ├─ stg_mcx__* → int_mcx__* → fct/dim/rpt_mcx_*   dbt build + tests
                   ├─ mcx_semantic_layer             MetricFlow answers for that commodity
                   ├─ okf                            knowledge bundle
                   ├─ wren_semantic_layer            every Wren model and cube planned + bound
                   └─ mcx_report_site                evidence build, then the format audit
mcx_all_ingest             every commodity's load, then the downstream pass once (bulk)
mcx_transform_and_report   the dbt → metrics → Evidence → Wren half alone (a model or page change)
        │ any of the above succeeds
        ▼ sensor mcx_catalog_after_run
mcx_catalog_publish        catalog_sync (graph, MDL, OpenMetadata tables, glossary, metrics)
                           → mcx_catalog (Commodities Ontology glossary, tiers, page lineage)
```

## Commodities

The `mcx_products` seed (`transform/seeds/mcx_products.csv`) is the catalogue:
one row per MCX contract code, grouped into the commodity its job is named for.
`sources/mcx.py` reads the same file, so the codes a job fetches are the codes
dbt models. Adding a commodity is a seed row (and, if it should start paused, a
line in `src/commodity_india/defs/mcx_jobs.yaml`); the job, schedule and report page appear on reload.

## Pause, resume, run now — any time

Dagster owns schedule state; `src/commodity_india/defs/mcx_jobs.yaml` only sets the state a schedule is
created in.

| Want | UI | CLI (from the repo root) |
|---|---|---|
| Pause one commodity | Automation → `mcx_gold_daily` → off | `dagster schedule stop mcx_gold_daily -w platform/workspace.yaml -l commodity__commodity-india` |
| Resume it | toggle on | `dagster schedule start mcx_gold_daily …` |
| Run it now | Jobs → `mcx_gold_ingest` → Materialize | `dagster job launch -j mcx_gold_ingest …` |
| Rerun every commodity (backfill, a missed morning) | Jobs → `mcx_all_ingest` | `dagster job launch -j mcx_all_ingest …` |
| Rebuild without loading | Jobs → `mcx_transform_and_report` | `dagster job launch -j mcx_transform_and_report …` |
| Publish the catalogue now | Jobs → `mcx_catalog_publish` | `dagster job launch -j mcx_catalog_publish …` |
| Stop a running load | Runs → Terminate | — |
| Without Dagster | — | `uv run python -m commodity_india.sources.mcx gold silver` (from `src/`) |

Terminating is safe: a load commits in batches of `max_contracts_per_batch`
contracts (rows and cursors together), and the commodity's next run resumes
after the last committed batch. dbt and Evidence are steps of the same job, so
they run only after that commodity's load succeeded. In Dagster, `tag:mcx`
selects every MCX asset — loaders, raw tables, dbt models, the Evidence build.

**Reruns are safe at any time, for any commodity, in any number.** dlt merges
on each table's natural key and resumes from each contract's cursor, re-reading
the last `refetch_days`; dbt rebuilds the MCX models; the semantic check, Wren
check and site are rebuilt from the warehouse. Rerunning a day, a week or the
whole history converges on the same tables. Runs launched together do not
collide: every step that opens the warehouse (loads, dbt, MetricFlow, Evidence,
the Wren check, the catalogue sync) queues on the project's writer pool, limit
1 per step (`.dagster/dagster.yaml`), so runs interleave step by step.

## What fails a run, and what does not

| Step | Fails the run when |
|---|---|
| `mcx_<c>` | MCX does not answer (`MCXUnavailable` names the route), or a batch makes no progress |
| `mcx_landed_tables` | the commodity landed no futures rows — dbt never builds marts over nothing |
| `_dbt` | a model or test fails (two singular tests are `warn`) |
| `mcx_semantic_layer` | MetricFlow cannot answer the per-code or per-commodity metrics for that commodity |
| `mcx_report_site` | `npm run sources`/`build` fails, or `pf report audit` finds an error: a declared-format mismatch (`fmt-unit`, `fmt-missing`) or a rendered value that is NaN, undefined, a raw float or scientific notation (`fmt-rendered`) |
| `wren_semantic_layer` | never; its findings are warnings and the `workspace_check` metadata |
| catalogue | never fails a data run. It is its own job, launched by the sensor. Without `OPENMETADATA_JWT_TOKEN` in the Dagster process, the sensor skips and shows why |

## OpenMetadata

The catalogue job needs the `ingestion-bot` token in the environment of the
process that runs Dagster. It is never written to a file:

```bash
export OPENMETADATA_JWT_TOKEN=…   # Settings → Bots → ingestion-bot in the OpenMetadata UI
export OPENMETADATA_HOST_PORT=http://localhost:8585/api   # the default
dagster dev -w platform/workspace.yaml
```

Inside the platform stack, `pf.stack.token` resolves it at start and nothing
has to be exported.

## Knobs — `.dlt/config.toml` `[sources.mcx]`

| Key | Default | Effect |
|---|---|---|
| `history_start` | 2021-01-01 | first day fetched for a new contract; earlier moves backfill only what is missing |
| `options_history_days` | 45 | depth of option chains kept (hundreds of strikes a day) |
| `refetch_days` | 5 | overlap re-read per active contract, so revised settlements land |
| `max_contracts_per_batch` | 40 | contracts per committed batch |
| `pause_seconds` | 0.25 | spacing between requests to MCX |
| `strategy` | contract | `datewise` uses mcxlib → mcxpy → direct, first that answers |

Env overrides: `SOURCES__MCX__HISTORY_START=2016-01-01`, etc.

## When a load fails

* `MCXUnavailable: … answered text/html instead of JSON` — MCX moved a route or
  Akamai blocked the request. Open `https://www.mcxindia.com/market-data/bhavcopy`
  in a browser, find the new `GetData(...)` method in `/assets/customjs/BhavCopy.js`.
* `every contract failed` — the feed is down for that commodity; other
  commodities are unaffected. Retry the job later.
* `batch N made no progress` — a planning bug (a contract re-planned every
  batch); the load stops instead of looping. See `tests/test_mcx_feed.py`.
* Monday freshness is the calendar; a midweek gap is the feed (project rule).

## Metrics — where they live

Everything is computed in `transform/models/marts/mcx/`; pages only select.

| Mart | Grain | Holds |
|---|---|---|
| `fct_mcx_futures_daily` | contract × session | every expiry: OHLC, OI change, build-up, notional, volume/OI |
| `fct_mcx_commodity_daily` | code × session | returns 1d–1y/YTD, SMA 20/50/200, EMA/MACD, RSI, ATR, Bollinger, 52w range, drawdown, realised & Parkinson vol, OI build-up, calendar spread, carry, rollover, premium to landed parity, stance |
| `fct_mcx_options_daily` | chain × session | PCR (OI, volume), OI walls, max pain vs the underlying future |
| `dim_mcx_contracts` | contract | expiry calendar |
| `rpt_mcx_commodity_board` | code | latest everything — the summary page |

Indicators run on the most-active contract (highest OI) with returns taken
inside one contract and prices ratio back-adjusted, so a roll is never a move.
