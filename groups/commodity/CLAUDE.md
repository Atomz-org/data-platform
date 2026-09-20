# commodity — group context

@kg/group_card.md

Sister projects under `projects/` share this ontology instance, the conformed
dimensions in `shared/transform`, and group-level metrics. They have **separate
warehouses and run in parallel**.

## Business rules the graph cannot encode
- A price is a `unit_price`, never a `money_amount`: it is not additive. Never
  aggregate a price across commodities; a mean is a sum ÷ count ratio metric
  within one commodity.
- Convert minor-unit quotes first (`USX` = US cents, `GBX` = pence) with
  `to_major_currency`, then units, then FX. The order is not interchangeable.
- Unit codes and their factors live in the shared `units_of_measure` seed,
  built in each sister from the group package. Never hardcode 31.1035 or
  0.4536 in a model.
- A sister is a **market**: one row in the `markets` seed, one currency, one
  customs regime, one warehouse (`add-a-market`). The catalog, units, indicative
  benchmark levels and the connectors are the group's; a market's units, duty
  and exchange contracts are its own seeds, under the same names in every
  sister (`market_units`, `import_duties`).
- The conformed marts — `dim_commodities`, `fct_commodity_prices_daily`,
  `fct_fx_rates_daily`, `fct_landed_prices_daily`, `rpt_commodity_price_board`
  — and the semantic layer are identical SQL in every sister. Change them
  everywhere or nowhere; the roll-up unions them by name and refuses a
  sister whose columns differ.
- Customs duty is per market, so it belongs to a sister project, never here.
- dlt Core lands raw only: one dataset per source (`yahoo_finance`,
  `gold_api`; the roll-up's is `sisters`), types frozen, row counts read back. dbt owns the rest: staging generated 1:1 (`pf gen-staging`),
  currency, unit and FX conversion once in `intermediate` or a mart, grain in
  marts.
- Never transform inside a dlt resource. Never join in staging.

## Cross-entity work
Only the `commodity-rollup` project may read sister data, and only via ATTACH READ_ONLY.
Never read a sister project's files from another project.
