---
name: price-feed-triage
description: Classify a stale or empty price load before touching anything, calendar, feed, symbol, cursor or contract, from the load's row counts, the dlt trace and the two loops that surface it.
---
# Price feed triage

Classify first. A freshness breach on a daily candle feed has several causes
that look alike from the monitor, and only some of them are a defect.

## What the feeds do

- **Yahoo Finance** (`yahoo_finance`: `futures_prices`, `fx_rates`). The chart
  endpoint answers 429 without a browser User-Agent, so the source sends one.
  One request per symbol through `RESTClient`. A symbol that fails is logged
  and skipped, so one delisted contract never stops the rest; every symbol
  failing raises, so a dead feed never builds marts over an empty load and
  calls it green. Cursors live per symbol in `dlt.current.resource_state()`,
  advance only after that symbol's candles were yielded, and refetch a ten-day
  overlap, so a failed symbol retries its whole window next run and a missed
  week self-heals. The state travels with the destination: deleting the
  warehouse rebackfills every symbol, and so does changing `history_range`.
- **gold-api** (`gold_api`: `spot_prices`). A backup feed for the precious
  metals, declared as a `rest_api` source. 404, 429 and 5xx are ignored per
  symbol, and `seed.py` records a failed run as a warning. It only ever warns;
  it never fails a seed.
- **Indicative levels** (`indicative_prices` seed). Not a feed. Stale means
  nobody appended a newer `as_of_date`.

## The calendar rule

Futures do not settle at weekends, and `futures_prices` is keyed on the trading
day, not the load time, so every Monday the newest `trade_date` is Friday's. A
Monday freshness breach is the calendar, and the load that ran on schedule and
merged zero new rows proves it. A midweek breach with loads reporting `ok` and
zero rows merged is the feed: the User-Agent rejected, or a front-month symbol
delisted. FX fixes have the same gaps and `int_fx_rates__daily` carries the
last fix forward, so a landed price never waits for one. The eval cases
`futures_weekend_gap_is_market_closure` and
`futures_midweek_gap_is_a_feed_failure` pin both judgements.

## Where to look

1. **`rows`.** `run_source` reads row counts back through `pipeline.dataset()`
   and `pf seed` prints them per table
   (`dataset=yahoo_finance (futures_prices=N, fx_rates=N)`). A required source
   with an empty table stops the seed before dbt runs: the platform refusing to
   build marts over nothing.
2. **The trace.** `dlt pipeline <project>_<source> trace` and `failed-jobs`, as
   the `debug-pipeline` skill lays out. A `data_type: freeze` violation names
   the column the feed changed type on (`DEFAULT_CONTRACT`).
3. **The state.** `dlt pipeline <name> info` shows the cursors;
   `dlt pipeline <name> drop <resource>` rebackfills one resource (its tables
   and its state go).

## Which loop surfaces what

| Symptom | Loop | Answer |
|---|---|---|
| `max(trade_date)` older than the freshness allowance | `freshness-triage` | calendar (ignorable) or feed (escalate), by the rule above |
| `assert_every_commodity_is_priced`, a `relationships` test on `commodity_id`, a `not_null` on `close_price` | `test-failure-triage` | which upstream table landed empty or partial |

Fix the source, the contract or the catalog, then `pf seed`. Never edit a raw
table: the next load merges over it and the fix is gone, and the raw stage is
the one layer that must be rebuildable from the feed alone.
