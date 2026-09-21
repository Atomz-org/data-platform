# ADR-0005: commodity-india is one market of many

**Status:** accepted · 2026-09-20

## Context

This project began as the whole commodity tracker: it held the catalog of 33
benchmarks, the Yahoo and gold-api connectors, and an India landed price. A
second market (the United States) would have copied all of that and changed
the currency, and a third would have copied the copy. The group already had
the mechanism for what sisters share — `groups/commodity/shared`, a dbt package
of conformed seeds and macros — and the platform already had the shape for
what they do not: one project per legal entity, separate warehouses, a roll-up
that attaches them READ_ONLY.

## Decision

A sister is a **market**: one row in the group's `markets` seed (code,
currency, home exchange, owning project), one warehouse, one customs regime.

What moved to the group, because it is the same in every market:

- The catalog (`commodities` seed) and the indicative benchmark levels
  (`indicative_prices` seed). `stg_reference__commodities` and the `reference`
  dlt source are gone; `dim_commodities` reads the seed. A benchmark level is a
  fact about the benchmark, not about a market.
- The connectors (`commodity_shared.yahoo_finance`, `commodity_shared.gold_api`)
  and the catalog loader. Each sister's `sources/*.py` is now only the
  annotation — the sister's contract with its own staging layer.
- The conformed marts and the semantic layer: identical SQL in every sister,
  reading the market through `var('market_code')` and the market's own facts
  through seeds with conformed names. `fct_india_landed_prices_daily` became
  `fct_landed_prices_daily`, with `market_code`, `currency_code`,
  `usd_fx_rate`, `landed_price_local`, `duty_local` in place of the INR-named
  columns; `india_market_units` and `india_import_duties` became
  `market_units` and `import_duties`.

What stayed here, because it is India's: the duty schedule and its
confirmation dates (ADR-0001), the units Indian markets quote in, the MCX
contracts and retail purities, and the boards built on them.

## Consequences

- Metric names are conformed too: `avg_landed_price_local`, `avg_duty_local`,
  `avg_usd_fx_rate`. A metric asked of India can be asked of any sister by
  name; the currency is a dimension (`landed_price__currency_code`), not part
  of the name.
- The roll-up (`commodity-rollup`) unions `fct_landed_prices_daily` across
  sisters and refuses one whose columns differ. Changing a conformed model
  here means changing it in every sister — `test_conformed_models_are_identical`
  in the group's shared tests says which files drifted.
- Adding a market is the `add-a-market` skill: a registry row, a scaffold, the
  market's seeds, the conformed models copied unchanged.
