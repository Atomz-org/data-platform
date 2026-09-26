# Metrics

## Cube `commodity_india_core` on `fct_commodity_trading_signals_daily`

Ask it with `wren cube query --cube <name> --measures <m> --dimensions <d>`; the
engine writes the GROUP BY.

Measures:

| measure | expression | meaning |
|---|---|---|
| `attribution_days` | `count(price_id)` | Attribution Days |
| `avg_benchmark_price_usd` | `sum(close_price) / nullif(count(close_price), 0)` | Avg Benchmark Price (USD) |
| `avg_duty_local` | `sum(duty_local) / nullif(count(landed_price_local), 0)` | Avg Customs Duty (market currency) |
| `avg_fx_share_of_move` | `sum(fx_share_of_move) / nullif(count(fx_share_of_move), 0)` | Avg Rupee Share of the Move |
| `avg_landed_price_local` | `sum(landed_price_local) / nullif(count(landed_price_local), 0)` | Avg Landed Price (market currency) |
| `avg_momentum_20d` | `sum(momentum_20d_pct) / nullif(count(momentum_20d_pct), 0)` | Avg 20-Day Momentum |
| `avg_range_position` | `sum(pct_of_52w_range) / nullif(count(pct_of_52w_range), 0)` | Avg Position in 52-Week Range |
| `avg_realised_vol` | `sum(realised_vol_20d) / nullif(count(realised_vol_20d), 0)` | Avg Realised Volatility (annualised) |
| `avg_usd_fx_rate` | `sum(usd_fx_rate) / nullif(count(landed_price_local), 0)` | Avg Applied FX Rate |
| `benchmark_contribution_total` | `sum(benchmark_contribution_pct)` | Benchmark Contribution (component) |
| `benchmark_price_days` | `count(close_price)` | Priced Days |
| `benchmark_price_usd_total` | `sum(close_price)` | Benchmark Price Total (component) |
| `contracts_traded` | `sum(volume)` | Contracts Traded |
| `duty_contribution_total` | `sum(duty_contribution_pct)` | Duty Contribution (component) |
| `duty_local_total` | `sum(duty_local)` | Customs Duty Total (component) |
| `fx_contribution_total` | `sum(fx_contribution_pct)` | FX Contribution (component) |
| `fx_share_days` | `count(fx_share_of_move)` | Days With an FX Share |
| `fx_share_total` | `sum(fx_share_of_move)` | FX Share (component) |
| `landed_price_days` | `count(landed_price_local)` | Days With a Landed Price |
| `landed_price_local_total` | `sum(landed_price_local)` | Landed Price Total (component) |
| `momentum_20d_days` | `count(momentum_20d_pct)` | Days With a Momentum Reading |
| `momentum_20d_total` | `sum(momentum_20d_pct)` | 20-Day Momentum (component) |
| `period_high_price_usd` | `max(coalesce(high_price, close_price))` | Period High (USD) |
| `period_low_price_usd` | `min(coalesce(low_price, close_price))` | Period Low (USD) |
| `range_position_days` | `count(pct_of_52w_range)` | Days With a Range Position |
| `range_position_total` | `sum(pct_of_52w_range)` | Range Position (component) |
| `realised_vol_days` | `count(realised_vol_20d)` | Days With a Volatility Reading |
| `realised_vol_total` | `sum(realised_vol_20d)` | Realised Volatility (component) |
| `signal_days` | `count(price_id)` | Signal Days |
| `usd_fx_rate_total` | `sum(usd_fx_rate)` | Applied FX Rate Total (component) |

Dimensions: `category`, `commodity_id`, `commodity_name`, `currency_code`, `exchange`, `is_carried_forward`, `is_duty_rate_confirmed`, `is_import_prohibited`, `ma_crossover`, `ma_regime`, `market_code`, `market_unit`, `price_basis`, `primary_driver`, `quote_currency_code`, `quote_unit`, `segment`, `stance`, `volatility_regime`
Time dimensions: `price_date`, `rate_date`

## Metric definitions

The governed definitions, as the semantic layer declares them.

| metric | type | model | how | unit | filter | meaning |
|---|---|---|---|---|---|---|
| `attribution_days` | simple | `fct_landed_price_attribution_daily` | `count(price_id)` |  |  | Attribution Days |
| `avg_benchmark_price_usd` | ratio | `fct_commodity_prices_daily` | `benchmark_price_usd_total / benchmark_price_days` |  |  | Mean daily settlement price, USD per quote unit. Group by commodity. |
| `avg_duty_local` | ratio | `fct_landed_prices_daily` | `duty_local_total / landed_price_days` |  |  | Mean customs duty per market unit, in this market's currency. Group by commodity. |
| `avg_fx_share_of_move` | ratio | `fct_landed_price_attribution_daily` | `fx_share_total / fx_share_days` |  |  | Share of the 20-day landed move attributable to USD/INR rather than the benchmark or duty. High means the commodity call and the currency call have come apart, and timing the commodity will not recover the cost. |
| `avg_landed_price_local` | ratio | `fct_landed_prices_daily` | `landed_price_local_total / landed_price_days` |  |  | Mean import landed price in this market's currency per its market unit (benchmark × USD/local × (1 + duty)). Group by commodity; filter landed_price__is_duty_rate_confirmed to exclude history priced at a back-applied duty rate. |
| `avg_momentum_20d` | ratio | `fct_commodity_trading_signals_daily` | `momentum_20d_total / momentum_20d_days` |  |  | Mean 20-day rate of change. Group by commodity. |
| `avg_range_position` | ratio | `fct_commodity_trading_signals_daily` | `range_position_total / range_position_days` |  |  | 0 at the 52-week low, 1 at the high. Group by commodity — averaging this across commodities is a number about the basket, not about anything tradable. |
| `avg_realised_vol` | ratio | `fct_commodity_trading_signals_daily` | `realised_vol_total / realised_vol_days` |  |  | 20-day dispersion annualised on 252 trading days. Group by commodity. |
| `avg_usd_fx_rate` | ratio | `fct_landed_prices_daily` | `usd_fx_rate_total / landed_price_days` |  |  | Mean units of this market's currency per US dollar, as applied to landed prices; 1 for a USD market. |
| `benchmark_contribution_total` | simple | `fct_landed_price_attribution_daily` | `sum(benchmark_contribution_pct)` |  |  | Benchmark Contribution (component) |
| `benchmark_price_days` | simple | `fct_commodity_prices_daily` | `count(close_price)` |  |  | Days with a benchmark price. Group by commodity to spot feed gaps. |
| `benchmark_price_mom_change` | derived | `fct_commodity_prices_daily` | `derived` |  |  | Month-over-month change in the mean benchmark price. Group by commodity. |
| `benchmark_price_usd_total` | simple | `fct_commodity_prices_daily` | `sum(close_price)` |  |  | Building block for avg_benchmark_price_usd. A sum of prices means nothing on its own. |
| `contracts_traded` | simple | `fct_commodity_prices_daily` | `sum(volume)` |  | price_basis = 'futures' | Front-month futures volume from live feeds. Group by commodity. |
| `duty_contribution_total` | simple | `fct_landed_price_attribution_daily` | `sum(duty_contribution_pct)` |  |  | Duty Contribution (component) |
| `duty_local_total` | simple | `fct_landed_prices_daily` | `sum(duty_local)` |  |  | Building block for avg_duty_local. A sum of per-unit duties means nothing on its own. |
| `fx_contribution_total` | simple | `fct_landed_price_attribution_daily` | `sum(fx_contribution_pct)` |  |  | Signed rupee contribution summed over days. Group by commodity. |
| `fx_share_days` | simple | `fct_landed_price_attribution_daily` | `count(fx_share_of_move)` |  |  | Days With an FX Share |
| `fx_share_total` | simple | `fct_landed_price_attribution_daily` | `sum(fx_share_of_move)` |  |  | FX Share (component) |
| `landed_price_days` | simple | `fct_landed_prices_daily` | `count(landed_price_local)` |  |  | Days a landed price exists — never for commodities this market prohibits importing. |
| `landed_price_local_total` | simple | `fct_landed_prices_daily` | `sum(landed_price_local)` |  |  | Building block for avg_landed_price_local. A sum of prices means nothing on its own. |
| `landed_price_mom_change` | derived | `fct_landed_prices_daily` | `derived` |  |  | Month-over-month change in the mean landed price; moves with both the benchmark and the currency. |
| `momentum_20d_days` | simple | `fct_commodity_trading_signals_daily` | `count(momentum_20d_pct)` |  |  | Days With a Momentum Reading |
| `momentum_20d_total` | simple | `fct_commodity_trading_signals_daily` | `sum(momentum_20d_pct)` |  |  | 20-Day Momentum (component) |
| `period_high_price_usd` | simple | `fct_commodity_prices_daily` | `max(coalesce(high_price, close_price))` |  |  | Highest traded price in the period, USD per quote unit. Group by commodity. |
| `period_low_price_usd` | simple | `fct_commodity_prices_daily` | `min(coalesce(low_price, close_price))` |  |  | Lowest traded price in the period, USD per quote unit. Group by commodity. |
| `range_position_days` | simple | `fct_commodity_trading_signals_daily` | `count(pct_of_52w_range)` |  |  | Days With a Range Position |
| `range_position_total` | simple | `fct_commodity_trading_signals_daily` | `sum(pct_of_52w_range)` |  |  | Sum of daily range positions. A component of avg_range_position, not a figure to read. |
| `realised_vol_days` | simple | `fct_commodity_trading_signals_daily` | `count(realised_vol_20d)` |  |  | Days With a Volatility Reading |
| `realised_vol_total` | simple | `fct_commodity_trading_signals_daily` | `sum(realised_vol_20d)` |  |  | Realised Volatility (component) |
| `signal_days` | simple | `fct_commodity_trading_signals_daily` | `count(price_id)` |  |  | Days with a signal reading. The denominator every mean below divides by. |
| `usd_fx_rate_total` | simple | `fct_landed_prices_daily` | `sum(usd_fx_rate)` |  |  | Building block for avg_usd_fx_rate — the rate each landed price actually used. |
