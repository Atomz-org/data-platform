# Scope — groups/commodity/projects/commodity-rollup

This workspace is one project of the `commodity` group. Every model in it is a
mart of `commodity-rollup` (MDL catalog `commodity`, schema `commodity_rollup`),
addressed by its model name; the engine maps that name to the project's own warehouse.

- Answer only from the models, cubes and rules in this workspace. Another
  project's tables are not visible here and are never guessed at or joined.
- Columns that hold personal data are absent from this workspace by design.
  A question that needs one has no answer here, and saying so is the answer.
- Every query is planned through the MDL, dry-run, row-limited and recorded
  before it runs. Write one `SELECT` over model names exactly as listed.
- A governed number is its metric: answer it from the cube `fct_landed_prices_daily_metrics` or from `query_metrics`, never by recomputing it in SQL.
- A price is a unit price and a percentage is already a ratio: neither is
  summed or averaged across rows. Money is additive within one currency.

## Models

- `dim_commodities`
- `dim_markets`
- `fct_landed_prices_daily`
- `fct_market_spreads_daily`
- `rpt_market_comparison_board`
