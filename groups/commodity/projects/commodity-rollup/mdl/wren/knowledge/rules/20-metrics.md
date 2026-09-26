# Metrics

## Cube `fct_landed_prices_daily_metrics` on `fct_landed_prices_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_import_parity_ratio` | `sum(landed_price_usd_per_quote_unit) / nullif(sum(case when landed_price_usd_per_quote_unit is not null then benchmark_price_usd end), 0)` | Avg Import Parity Ratio |
| `avg_landed_price_usd` | `sum(landed_price_usd_per_quote_unit) / nullif(count(landed_price_usd_per_quote_unit), 0)` | Avg Landed Price (USD per quote unit) |
| `benchmark_usd_total_where_landed` | `sum(case when landed_price_usd_per_quote_unit is not null then benchmark_price_usd end)` | Benchmark USD Total, landed days (component) |
| `landed_usd_days` | `count(landed_price_usd_per_quote_unit)` | Days With a Comparable Landed Price |
| `landed_usd_total` | `sum(landed_price_usd_per_quote_unit)` | Landed USD Total (component) |

Dimensions: `commodity_id`, `is_duty_rate_confirmed`, `market_code`, `price_basis`
Time dimensions: `price_date`

## Cube `fct_market_spreads_daily_metrics` on `fct_market_spreads_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_spread_to_cheapest_ratio` | `sum(spread_to_cheapest_usd) / nullif(sum(cheapest_landed_usd), 0)` | Avg Spread to Cheapest Market (ratio) |
| `avg_spread_to_cheapest_usd` | `sum(spread_to_cheapest_usd) / nullif(count(spread_to_cheapest_usd), 0)` | Avg Spread to Cheapest Market (USD) |
| `cheapest_usd_total` | `sum(cheapest_landed_usd)` | Cheapest Landed Total (component) |
| `days_as_cheapest_market` | `sum(case when is_cheapest_market then 1 else 0 end)` | Days as Cheapest Market |
| `spread_days` | `count(spread_to_cheapest_usd)` | Days Compared |
| `spread_usd_total` | `sum(spread_to_cheapest_usd)` | Spread Total (component) |

Dimensions: `cheapest_market_code`, `commodity_id`, `is_cheapest_market`, `market_code`
Time dimensions: `price_date`

## Metric definitions

The governed definitions, as the semantic layer declares them.

| metric | type | model | how | unit | filter | meaning |
|---|---|---|---|---|---|---|
| `avg_import_parity_ratio` | ratio | `fct_landed_prices_daily` | `landed_usd_total / benchmark_usd_total_where_landed` |  |  | Landed over benchmark, both in USD per quote unit — 1.15 means landing adds 15%. Group by commodity and market. |
| `avg_landed_price_usd` | ratio | `fct_landed_prices_daily` | `landed_usd_total / landed_usd_days` |  |  | Mean landed price on the benchmark's footing. Group by commodity and market; this is the number that compares. |
| `avg_spread_to_cheapest_ratio` | ratio | `fct_market_spreads_daily` | `spread_usd_total / cheapest_usd_total` |  |  | Mean spread as a share of the cheapest landed price, re-divided at query grain. Group by commodity and market. |
| `avg_spread_to_cheapest_usd` | ratio | `fct_market_spreads_daily` | `spread_usd_total / spread_days` |  |  | Mean USD per quote unit a market pays over the cheapest market that day. Group by commodity and market. |
| `benchmark_usd_total_where_landed` | simple | `fct_landed_prices_daily` | `sum(case when landed_price_usd_per_quote_unit is not null then benchmark_price_usd end)` |  |  | Building block for avg_import_parity_ratio — the benchmark on exactly the days a landed price exists. |
| `cheapest_usd_total` | simple | `fct_market_spreads_daily` | `sum(cheapest_landed_usd)` |  |  | Building block for avg_spread_to_cheapest_ratio. |
| `days_as_cheapest_market` | simple | `fct_market_spreads_daily` | `sum(case when is_cheapest_market then 1 else 0 end)` |  |  | Days a market was the cheapest place to land a commodity. Group by commodity and market. |
| `landed_usd_days` | simple | `fct_landed_prices_daily` | `count(landed_price_usd_per_quote_unit)` |  |  | Days a market landed a commodity, restated in USD per quote unit. |
| `landed_usd_total` | simple | `fct_landed_prices_daily` | `sum(landed_price_usd_per_quote_unit)` |  |  | Building block for avg_landed_price_usd. A sum of prices means nothing on its own. |
| `spread_days` | simple | `fct_market_spreads_daily` | `count(spread_to_cheapest_usd)` |  |  | Days at least two markets priced the commodity. |
| `spread_usd_total` | simple | `fct_market_spreads_daily` | `sum(spread_to_cheapest_usd)` |  |  | Building block for avg_spread_to_cheapest_usd. |
