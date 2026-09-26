---
name: mcx-bhavcopy-feed
description: 'MCX bhavcopy: mcxlib/mcxpy routes retired, GET market-data/bhavcopy routes + mcxlib headers; per-commodity dlt pipelines; traps'
type: project
status: active
agent: claude-code
---

stack: [dlt Core RESTClient, mcxlib 0.4, mcxpy 0.0.3, DuckDB, dbt, MetricFlow, Dagster, Evidence]

- mcxlib/mcxpy POST `backpage.aspx/<Method>`: retired by MCX (404 page, Sept 2026);
  their /docs/*.xlsx reports 403. Live routes: GET
  `/market-data/bhavcopy/GetDateWiseBhavCopy` (InstrumentName, fromDate dd/mm/yyyy) and
  `.../GetCommoditywiseBhavCopy` (InstrumentName, Symbol, Expiry DDMONYYYY, fromDate,
  toDate). Contract list = JSON in `div#symbol-data` of the bhavcopy page.
- Akamai admits mcxlib's header profile, refuses a bare UA (403). Never send
  Content-Type/Content-Length on the GETs.
- Bhavcopy `Date` is MM/DD/YYYY; untraded rows print 0 open/high/low with close = carried
  settlement → null them, gate indicators on liquidity (`is_liquid`, stance `illiquid`).
- Batched loads: a set of already-fetched contract ids must be shared across batches
  (`fetched`), else active contracts re-plan forever; `load_commodity` raises on a
  no-progress batch. Cursors per contract in dlt state; `completed` once expiry passed.
- dlt reads `.dlt/config.toml` from cwd; Dagster runs in `<project>/src` → sources/mcx.py
  sets DLT_PROJECT_DIR. Other sources in this project have the same exposure.
- Market-local sources stage in `staging/<source>/` + `intermediate/<source>/`; the group
  conformance test exempts only those dirs for sources not in commodity_shared.
- Templated Evidence page `[commodity].md` makes pf report build emit exposure
  `report_mcx_[commodity]` (dbt ExposureNameDeprecation) — platform sanitiser fix pending.
- `pf kg build` backfills columns from information_schema across ALL schemas, incl.
  Recce's `base_*`: a stale baseline table adds phantom columns to the graph → MDL →
  Evidence extract (price-board broke on `usd_inr_rate`). Fix: rebuild the baseline
  (`dbt seed/run --target base --exclude tag:mcx`), not the extract. Platform fix pending:
  scope the backfill to the target schemas.
- Any dbt command with `--target base` rewrites target/manifest.json with base schemas;
  run `dbt parse` (dev) + `dbt docs generate` before `pf kg build`/`pf report build`, or
  every extract points at `base_marts`.
