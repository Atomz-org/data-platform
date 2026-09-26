# Metrics

## Cube `commodity_us_core` on `fct_commodity_prices_daily`

Ask it with `wren cube query --cube <name> --measures <m> --dimensions <d>`; the
engine writes the GROUP BY.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_benchmark_price_usd` | `sum(close_price) / nullif(count(close_price), 0)` | Avg Benchmark Price (USD) |
| `avg_duty_local` | `sum(duty_local) / nullif(count(landed_price_local), 0)` | Avg Customs Duty (market currency) |
| `avg_landed_price_local` | `sum(landed_price_local) / nullif(count(landed_price_local), 0)` | Avg Landed Price (market currency) |
| `avg_usd_fx_rate` | `sum(usd_fx_rate) / nullif(count(landed_price_local), 0)` | Avg Applied FX Rate |
| `benchmark_price_days` | `count(close_price)` | Priced Days |
| `benchmark_price_usd_total` | `sum(close_price)` | Benchmark Price Total (component) |
| `contracts_traded` | `sum(volume)` | Contracts Traded |
| `duty_local_total` | `sum(duty_local)` | Customs Duty Total (component) |
| `landed_price_days` | `count(landed_price_local)` | Days With a Landed Price |
| `landed_price_local_total` | `sum(landed_price_local)` | Landed Price Total (component) |
| `period_high_price_usd` | `max(coalesce(high_price, close_price))` | Period High (USD) |
| `period_low_price_usd` | `min(coalesce(low_price, close_price))` | Period Low (USD) |
| `usd_fx_rate_total` | `sum(usd_fx_rate)` | Applied FX Rate Total (component) |

Dimensions: `category`, `commodity_id`, `commodity_name`, `currency_code`, `exchange`, `is_carried_forward`, `is_duty_rate_confirmed`, `is_import_prohibited`, `market_code`, `market_unit`, `price_basis`, `quote_currency_code`, `quote_unit`, `segment`
Time dimensions: `price_date`, `rate_date`

## Metric definitions

The governed definitions, as the semantic layer declares them.

| metric | type | model | how | unit | filter | meaning |
|---|---|---|---|---|---|---|
| `avg_benchmark_price_usd` | ratio | `fct_commodity_prices_daily` | `benchmark_price_usd_total / benchmark_price_days` |  |  | Mean daily settlement price, USD per quote unit. Group by commodity. |
| `avg_duty_local` | ratio | `fct_landed_prices_daily` | `duty_local_total / landed_price_days` |  |  | Mean customs duty per market unit, in this market's currency. Group by commodity. |
| `avg_landed_price_local` | ratio | `fct_landed_prices_daily` | `landed_price_local_total / landed_price_days` |  |  | Mean import landed price in this market's currency per its market unit (benchmark × USD/local × (1 + duty)). Group by commodity; filter landed_price__is_duty_rate_confirmed to exclude history priced at a back-applied duty rate. |
| `avg_usd_fx_rate` | ratio | `fct_landed_prices_daily` | `usd_fx_rate_total / landed_price_days` |  |  | Mean units of this market's currency per US dollar, as applied to landed prices; 1 for a USD market. |
| `benchmark_price_days` | simple | `fct_commodity_prices_daily` | `count(close_price)` |  |  | Days with a benchmark price. Group by commodity to spot feed gaps. |
| `benchmark_price_mom_change` | derived | `fct_commodity_prices_daily` | `derived` |  |  | Month-over-month change in the mean benchmark price. Group by commodity. |
| `benchmark_price_usd_total` | simple | `fct_commodity_prices_daily` | `sum(close_price)` |  |  | Building block for avg_benchmark_price_usd. A sum of prices means nothing on its own. |
| `contracts_traded` | simple | `fct_commodity_prices_daily` | `sum(volume)` |  | price_basis = 'futures' | Front-month futures volume from live feeds. Group by commodity. |
| `duty_local_total` | simple | `fct_landed_prices_daily` | `sum(duty_local)` |  |  | Building block for avg_duty_local. A sum of per-unit duties means nothing on its own. |
| `landed_price_days` | simple | `fct_landed_prices_daily` | `count(landed_price_local)` |  |  | Days a landed price exists — never for commodities this market prohibits importing. |
| `landed_price_local_total` | simple | `fct_landed_prices_daily` | `sum(landed_price_local)` |  |  | Building block for avg_landed_price_local. A sum of prices means nothing on its own. |
| `landed_price_mom_change` | derived | `fct_landed_prices_daily` | `derived` |  |  | Month-over-month change in the mean landed price; moves with both the benchmark and the currency. |
| `period_high_price_usd` | simple | `fct_commodity_prices_daily` | `max(coalesce(high_price, close_price))` |  |  | Highest traded price in the period, USD per quote unit. Group by commodity. |
| `period_low_price_usd` | simple | `fct_commodity_prices_daily` | `min(coalesce(low_price, close_price))` |  |  | Lowest traded price in the period, USD per quote unit. Group by commodity. |
| `usd_fx_rate_total` | simple | `fct_landed_prices_daily` | `sum(usd_fx_rate)` |  |  | Building block for avg_usd_fx_rate — the rate each landed price actually used. |
