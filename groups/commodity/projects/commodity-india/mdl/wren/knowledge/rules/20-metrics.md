# Metrics

## Cube `fct_commodity_prices_daily_metrics` on `fct_commodity_prices_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_benchmark_price_usd` | `sum(close_price) / nullif(count(close_price), 0)` | Avg Benchmark Price (USD) |
| `benchmark_price_days` | `count(close_price)` | Priced Days |
| `benchmark_price_usd_total` | `sum(close_price)` | Benchmark Price Total (component) |
| `contracts_traded` | `sum(volume)` | Contracts Traded |
| `period_high_price_usd` | `max(coalesce(high_price, close_price))` | Period High (USD) |
| `period_low_price_usd` | `min(coalesce(low_price, close_price))` | Period Low (USD) |

Dimensions: `commodity_id`, `price_basis`
Time dimensions: `price_date`

## Cube `fct_commodity_trading_signals_daily_metrics` on `fct_commodity_trading_signals_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_momentum_20d` | `sum(momentum_20d_pct) / nullif(count(momentum_20d_pct), 0)` | Avg 20-Day Momentum |
| `avg_range_position` | `sum(pct_of_52w_range) / nullif(count(pct_of_52w_range), 0)` | Avg Position in 52-Week Range |
| `avg_realised_vol` | `sum(realised_vol_20d) / nullif(count(realised_vol_20d), 0)` | Avg Realised Volatility (annualised) |
| `momentum_20d_days` | `count(momentum_20d_pct)` | Days With a Momentum Reading |
| `momentum_20d_total` | `sum(momentum_20d_pct)` | 20-Day Momentum (component) |
| `range_position_days` | `count(pct_of_52w_range)` | Days With a Range Position |
| `range_position_total` | `sum(pct_of_52w_range)` | Range Position (component) |
| `realised_vol_days` | `count(realised_vol_20d)` | Days With a Volatility Reading |
| `realised_vol_total` | `sum(realised_vol_20d)` | Realised Volatility (component) |
| `signal_days` | `count(price_id)` | Signal Days |

Dimensions: `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
Time dimensions: `price_date`

## Cube `fct_landed_price_attribution_daily_metrics` on `fct_landed_price_attribution_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `attribution_days` | `count(price_id)` | Attribution Days |
| `avg_fx_share_of_move` | `sum(fx_share_of_move) / nullif(count(fx_share_of_move), 0)` | Avg Rupee Share of the Move |
| `benchmark_contribution_total` | `sum(benchmark_contribution_pct)` | Benchmark Contribution (component) |
| `duty_contribution_total` | `sum(duty_contribution_pct)` | Duty Contribution (component) |
| `fx_contribution_total` | `sum(fx_contribution_pct)` | FX Contribution (component) |
| `fx_share_days` | `count(fx_share_of_move)` | Days With an FX Share |
| `fx_share_total` | `sum(fx_share_of_move)` | FX Share (component) |

Dimensions: `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `primary_driver`
Time dimensions: `price_date`

## Cube `fct_landed_prices_daily_metrics` on `fct_landed_prices_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_duty_local` | `sum(duty_local) / nullif(count(landed_price_local), 0)` | Avg Customs Duty (market currency) |
| `avg_landed_price_local` | `sum(landed_price_local) / nullif(count(landed_price_local), 0)` | Avg Landed Price (market currency) |
| `avg_usd_fx_rate` | `sum(usd_fx_rate) / nullif(count(landed_price_local), 0)` | Avg Applied FX Rate |
| `duty_local_total` | `sum(duty_local)` | Customs Duty Total (component) |
| `landed_price_days` | `count(landed_price_local)` | Days With a Landed Price |
| `landed_price_local_total` | `sum(landed_price_local)` | Landed Price Total (component) |
| `usd_fx_rate_total` | `sum(usd_fx_rate)` | Applied FX Rate Total (component) |

Dimensions: `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `market_unit`, `price_basis`
Time dimensions: `price_date`

## Cube `fct_mcx_commodity_daily_metrics` on `fct_mcx_commodity_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `avg_mcx_daily_return` | `sum(return_1d) / nullif(count(continuous_id), 0)` | Avg MCX Daily Return |
| `avg_mcx_garman_klass_vol_30d` | `sum(garman_klass_vol_30d) / nullif(count(garman_klass_vol_30d), 0)` | Avg MCX Garman–Klass Volatility, 30 sessions (annualised) |
| `avg_mcx_parkinson_vol_30d` | `sum(parkinson_vol_30d) / nullif(count(parkinson_vol_30d), 0)` | Avg MCX Parkinson Volatility, 30 sessions (annualised) |
| `avg_mcx_premium_to_landed` | `sum(premium_to_landed_pct) / nullif(count(premium_to_landed_pct), 0)` | Avg MCX Premium to Landed Parity |
| `avg_mcx_realised_vol` | `sum(realised_vol_20d) / nullif(count(realised_vol_20d), 0)` | Avg MCX Realised Volatility (annualised) |
| `avg_mcx_rogers_satchell_vol_30d` | `sum(rogers_satchell_vol_30d) / nullif(count(rogers_satchell_vol_30d), 0)` | Avg MCX Rogers–Satchell Volatility, 30 sessions (annualised) |
| `avg_mcx_roll_yield` | `sum(roll_yield_annualised) / nullif(count(roll_yield_annualised), 0)` | Avg MCX Roll Yield (annualised) |
| `avg_mcx_rsi` | `sum(rsi_14) / nullif(count(rsi_14), 0)` | Avg MCX RSI(14) |
| `mcx_backwardation_days` | `sum(case when is_backwardation then 1 else 0 end)` | MCX Sessions in Backwardation |
| `mcx_contango_days` | `sum(case when is_contango then 1 else 0 end)` | MCX Sessions in Contango |
| `mcx_contango_share` | `sum(case when is_contango then 1 else 0 end) / nullif(count(continuous_id), 0)` | MCX Share of Sessions in Contango |
| `mcx_gk_vol_30d_days` | `count(garman_klass_vol_30d)` | MCX Days With a Garman–Klass Reading |
| `mcx_gk_vol_30d_total` | `sum(garman_klass_vol_30d)` | MCX Garman–Klass Vol 30d (component) |
| `mcx_parkinson_vol_30d_days` | `count(parkinson_vol_30d)` | MCX Days With a Parkinson Reading |
| `mcx_parkinson_vol_30d_total` | `sum(parkinson_vol_30d)` | MCX Parkinson Vol 30d (component) |
| `mcx_premium_days` | `count(premium_to_landed_pct)` | MCX Days With a Parity Reading |
| `mcx_premium_total` | `sum(premium_to_landed_pct)` | MCX Premium to Landed Parity (component) |
| `mcx_realised_vol_days` | `count(realised_vol_20d)` | MCX Days With a Volatility Reading |
| `mcx_realised_vol_total` | `sum(realised_vol_20d)` | MCX Realised Volatility (component) |
| `mcx_return_total` | `sum(return_1d)` | MCX Summed Daily Return (component) |
| `mcx_roll_yield_days` | `count(roll_yield_annualised)` | MCX Days With a Roll Yield |
| `mcx_roll_yield_total` | `sum(roll_yield_annualised)` | MCX Roll Yield (component) |
| `mcx_rs_vol_30d_days` | `count(rogers_satchell_vol_30d)` | MCX Days With a Rogers–Satchell Reading |
| `mcx_rs_vol_30d_total` | `sum(rogers_satchell_vol_30d)` | MCX Rogers–Satchell Vol 30d (component) |
| `mcx_rsi_days` | `count(rsi_14)` | MCX Days With an RSI Reading |
| `mcx_rsi_total` | `sum(rsi_14)` | MCX RSI (component) |
| `mcx_session_days` | `count(continuous_id)` | MCX Sessions |
| `mcx_turnover_inr` | `sum(turnover_inr)` | MCX Futures Turnover (₹) |
| `mcx_volume_lots` | `sum(volume_lots)` | MCX Futures Volume (lots) |

Dimensions: `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
Time dimensions: `trade_date`

## Cube `fct_mcx_commodity_rollup_daily_metrics` on `fct_mcx_commodity_rollup_daily`

Ask it with `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <name> --measures <m>
--dimensions <d>`: the engine writes the GROUP BY and the gate runs it. Only this
cube's own measures and dimensions go together.

Measures:

| measure | expression | meaning |
|---|---|---|
| `mcx_commodity_avg_daily_return` | `sum(return_1d) / nullif(count(return_1d), 0)` | Avg Daily Return (flagship) — per Commodity |
| `mcx_commodity_avg_premium_to_landed` | `sum(premium_to_landed_pct) / nullif(count(premium_to_landed_pct), 0)` | Avg MCX Premium to Landed Parity — per Commodity |
| `mcx_commodity_avg_roll_yield` | `sum(roll_yield_annualised) / nullif(count(roll_yield_annualised), 0)` | Avg Roll Yield (annualised) — per Commodity |
| `mcx_commodity_avg_rsi` | `sum(rsi_14) / nullif(count(rsi_14), 0)` | Avg RSI(14) (flagship) — per Commodity |
| `mcx_commodity_backwardation_sessions` | `sum(is_backwardation_session)` | Sessions in Backwardation — per Commodity |
| `mcx_commodity_backwardation_share` | `sum(is_backwardation_session) / nullif(count(commodity_day_id), 0)` | Share of Sessions in Backwardation — per Commodity |
| `mcx_commodity_call_oi_notional_inr` | `sum(call_oi_notional_inr)` | Call Open Interest, Notional (component) — per Commodity |
| `mcx_commodity_close_var_days` | `count(sq_log_return_1d)` | Sessions With a Close-to-Close Reading — per Commodity |
| `mcx_commodity_close_var_total` | `sum(252 * sq_log_return_1d)` | Close-to-Close Variance (component) — per Commodity |
| `mcx_commodity_close_variance` | `sum(252 * sq_log_return_1d) / nullif(count(sq_log_return_1d), 0)` | Realised Variance, Close-to-Close (annualised) — per Commodity |
| `mcx_commodity_contango_sessions` | `sum(is_contango_session)` | Sessions in Contango — per Commodity |
| `mcx_commodity_contango_share` | `sum(is_contango_session) / nullif(count(commodity_day_id), 0)` | Share of Sessions in Contango — per Commodity |
| `mcx_commodity_gk_var_days` | `count(var_garman_klass)` | Sessions With a Garman–Klass Reading — per Commodity |
| `mcx_commodity_gk_var_total` | `sum(252 * var_garman_klass)` | Garman–Klass Variance (component) — per Commodity |
| `mcx_commodity_gk_variance` | `sum(252 * var_garman_klass) / nullif(count(var_garman_klass), 0)` | Garman–Klass Variance (annualised) — per Commodity |
| `mcx_commodity_hit_rate` | `sum(is_up_session) / nullif(count(return_1d), 0)` | Hit Rate (share of up sessions) — per Commodity |
| `mcx_commodity_log_return` | `sum(log_return_1d)` | Period Log Return (flagship) — per Commodity |
| `mcx_commodity_mini_turnover_inr` | `sum(mini_turnover_inr)` | Mini-Contract Turnover (component) — per Commodity |
| `mcx_commodity_mini_turnover_share` | `sum(mini_turnover_inr) / nullif(sum(turnover_inr), 0)` | Mini-Contract Share of Turnover — per Commodity |
| `mcx_commodity_oi_value_inr` | `sum(open_interest_value_inr)` | Open Interest Value (₹) — per Commodity |
| `mcx_commodity_option_notional_turnover_inr` | `sum(option_notional_turnover_inr)` | Options Notional Turnover (₹) — per Commodity |
| `mcx_commodity_option_premium_turnover_inr` | `sum(option_premium_turnover_inr)` | Options Premium Turnover (₹) — per Commodity |
| `mcx_commodity_parkinson_var_days` | `count(var_parkinson)` | Sessions With a Parkinson Reading — per Commodity |
| `mcx_commodity_parkinson_var_total` | `sum(252 * var_parkinson)` | Parkinson Variance (component) — per Commodity |
| `mcx_commodity_parkinson_variance` | `sum(252 * var_parkinson) / nullif(count(var_parkinson), 0)` | Parkinson Variance (annualised) — per Commodity |
| `mcx_commodity_premium_days` | `count(premium_to_landed_pct)` | Sessions With a Parity Reading — per Commodity |
| `mcx_commodity_premium_total` | `sum(premium_to_landed_pct)` | Landed-Parity Premium (component) — per Commodity |
| `mcx_commodity_put_call_ratio` | `sum(put_oi_notional_inr) / nullif(sum(call_oi_notional_inr), 0)` | Put/Call Ratio (notional OI) — per Commodity |
| `mcx_commodity_put_oi_notional_inr` | `sum(put_oi_notional_inr)` | Put Open Interest, Notional (component) — per Commodity |
| `mcx_commodity_return_days` | `count(return_1d)` | Sessions With a Return — per Commodity |
| `mcx_commodity_return_total` | `sum(return_1d)` | Daily Return (component) — per Commodity |
| `mcx_commodity_roll_yield_days` | `count(roll_yield_annualised)` | Sessions With a Roll Yield — per Commodity |
| `mcx_commodity_roll_yield_total` | `sum(roll_yield_annualised)` | Roll Yield (component) — per Commodity |
| `mcx_commodity_rs_var_days` | `count(var_rogers_satchell)` | Sessions With a Rogers–Satchell Reading — per Commodity |
| `mcx_commodity_rs_var_total` | `sum(252 * var_rogers_satchell)` | Rogers–Satchell Variance (component) — per Commodity |
| `mcx_commodity_rs_variance` | `sum(252 * var_rogers_satchell) / nullif(count(var_rogers_satchell), 0)` | Rogers–Satchell Variance (annualised) — per Commodity |
| `mcx_commodity_rsi_days` | `count(rsi_14)` | Sessions With an RSI Reading — per Commodity |
| `mcx_commodity_rsi_total` | `sum(rsi_14)` | RSI (component) — per Commodity |
| `mcx_commodity_sessions` | `count(commodity_day_id)` | Sessions — per Commodity |
| `mcx_commodity_turnover_inr` | `sum(turnover_inr)` | Futures Turnover (₹) — per Commodity |
| `mcx_commodity_up_sessions` | `sum(is_up_session)` | Up Sessions — per Commodity |
| `mcx_commodity_volume_flagship_lots` | `sum(volume_flagship_lots)` | Volume (flagship-lot equivalents) — per Commodity |

Dimensions: `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
Time dimensions: `trade_date`

## Metric definitions

The governed definitions, as the semantic layer declares them.

| metric | type | model | how | unit | filter | meaning |
|---|---|---|---|---|---|---|
| `attribution_days` | simple | `fct_landed_price_attribution_daily` | `count(price_id)` |  |  | Attribution Days |
| `avg_benchmark_price_usd` | ratio | `fct_commodity_prices_daily` | `benchmark_price_usd_total / benchmark_price_days` |  |  | Mean daily settlement price, USD per quote unit. Group by commodity. |
| `avg_duty_local` | ratio | `fct_landed_prices_daily` | `duty_local_total / landed_price_days` |  |  | Mean customs duty per market unit, in this market's currency. Group by commodity. |
| `avg_fx_share_of_move` | ratio | `fct_landed_price_attribution_daily` | `fx_share_total / fx_share_days` |  |  | Share of the 20-day landed move attributable to USD/INR rather than the benchmark or duty. High means the commodity call and the currency call have come apart, and timing the commodity will not recover the cost. |
| `avg_landed_price_local` | ratio | `fct_landed_prices_daily` | `landed_price_local_total / landed_price_days` |  |  | Mean import landed price in this market's currency per its market unit (benchmark × USD/local × (1 + duty)). Group by commodity; filter landed_price__is_duty_rate_confirmed to exclude history priced at a back-applied duty rate. |
| `avg_mcx_daily_return` | ratio | `fct_mcx_commodity_daily` | `mcx_return_total / mcx_session_days` |  |  | Mean roll-free daily return of the most-active contract. Group by contract_code. |
| `avg_mcx_garman_klass_vol_30d` | ratio | `fct_mcx_commodity_daily` | `mcx_gk_vol_30d_total / mcx_gk_vol_30d_days` |  |  | Garman–Klass (1980) range estimator from open, high, low and close over 30 sessions, annualised on 252. About 7× as efficient as close-to-close; it understates risk that happens overnight. Group by contract_code. |
| `avg_mcx_parkinson_vol_30d` | ratio | `fct_mcx_commodity_daily` | `mcx_parkinson_vol_30d_total / mcx_parkinson_vol_30d_days` |  |  | High–low range estimator over 30 sessions, annualised on 252. Group by contract_code. |
| `avg_mcx_premium_to_landed` | ratio | `fct_mcx_commodity_daily` | `mcx_premium_total / mcx_premium_days` |  |  | MCX settlement over the landed import-parity price of the same quote basis, minus one. Only codes the family prices. Group by contract_code. |
| `avg_mcx_realised_vol` | ratio | `fct_mcx_commodity_daily` | `mcx_realised_vol_total / mcx_realised_vol_days` |  |  | 20-session close-to-close dispersion annualised on 252 sessions. Group by contract_code. |
| `avg_mcx_rogers_satchell_vol_30d` | ratio | `fct_mcx_commodity_daily` | `mcx_rs_vol_30d_total / mcx_rs_vol_30d_days` |  |  | Drift-robust OHLC range estimator over 30 sessions, annualised on 252. Group by contract_code. |
| `avg_mcx_roll_yield` | ratio | `fct_mcx_commodity_daily` | `mcx_roll_yield_total / mcx_roll_yield_days` |  |  | What a long earns rolling the near month into the next, annualised — negative in contango, positive in backwardation. Group by contract_code. |
| `avg_mcx_rsi` | ratio | `fct_mcx_commodity_daily` | `mcx_rsi_total / mcx_rsi_days` |  |  | Wilder RSI on the roll-free continuous series. Group by contract_code. |
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
| `mcx_backwardation_days` | simple | `fct_mcx_commodity_daily` | `sum(case when is_backwardation then 1 else 0 end)` |  |  | MCX Sessions in Backwardation |
| `mcx_commodity_avg_daily_return` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_return_total / mcx_commodity_return_days` |  |  | Avg Daily Return (flagship) — per Commodity |
| `mcx_commodity_avg_premium_to_landed` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_premium_total / mcx_commodity_premium_days` |  |  | MCX settlement over benchmark × USD/INR × (1 + duty) for the same quote basis, minus one. Only commodities the family prices. |
| `mcx_commodity_avg_roll_yield` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_roll_yield_total / mcx_commodity_roll_yield_days` |  |  | What a long earned rolling the flagship's near month into the next, annualised. Negative in contango. |
| `mcx_commodity_avg_rsi` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_rsi_total / mcx_commodity_rsi_days` |  |  | Avg RSI(14) (flagship) — per Commodity |
| `mcx_commodity_backwardation_sessions` | simple | `fct_mcx_commodity_rollup_daily` | `sum(is_backwardation_session)` |  |  | Sessions in Backwardation — per Commodity |
| `mcx_commodity_backwardation_share` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_backwardation_sessions / mcx_commodity_sessions` |  |  | Share of Sessions in Backwardation — per Commodity |
| `mcx_commodity_call_oi_notional_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(call_oi_notional_inr)` |  |  | Call Open Interest, Notional (component) — per Commodity |
| `mcx_commodity_close_var_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(sq_log_return_1d)` |  |  | Sessions With a Close-to-Close Reading — per Commodity |
| `mcx_commodity_close_var_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(252 * sq_log_return_1d)` |  |  | Close-to-Close Variance (component) — per Commodity |
| `mcx_commodity_close_variance` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_close_var_total / mcx_commodity_close_var_days` |  |  | Zero-mean realised variance of the flagship's daily log returns, × 252. Its square root is realised volatility over whatever window the query asks for. |
| `mcx_commodity_contango_sessions` | simple | `fct_mcx_commodity_rollup_daily` | `sum(is_contango_session)` |  |  | Sessions in Contango — per Commodity |
| `mcx_commodity_contango_share` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_contango_sessions / mcx_commodity_sessions` |  |  | Share of Sessions in Contango — per Commodity |
| `mcx_commodity_gk_var_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(var_garman_klass)` |  |  | Sessions With a Garman–Klass Reading — per Commodity |
| `mcx_commodity_gk_var_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(252 * var_garman_klass)` |  |  | Garman–Klass Variance (component) — per Commodity |
| `mcx_commodity_gk_variance` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_gk_var_total / mcx_commodity_gk_var_days` |  |  | Garman–Klass (1980) OHLC variance per session, × 252. The most efficient of the four for a zero-drift market; blind to the overnight gap. |
| `mcx_commodity_gk_vol` | derived | `fct_mcx_commodity_rollup_daily` | `derived` |  |  | Garman–Klass Volatility (annualised) — per Commodity |
| `mcx_commodity_hit_rate` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_up_sessions / mcx_commodity_return_days` |  |  | Sessions the flagship settled higher, over sessions with a return. |
| `mcx_commodity_log_return` | simple | `fct_mcx_commodity_rollup_daily` | `sum(log_return_1d)` |  |  | Sum of the flagship's roll-free daily log returns — additive over time; exp(x) − 1 is the period return. |
| `mcx_commodity_mini_turnover_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(mini_turnover_inr)` |  |  | Mini-Contract Turnover (component) — per Commodity |
| `mcx_commodity_mini_turnover_share` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_mini_turnover_inr / mcx_commodity_turnover_inr` |  |  | Turnover in the non-flagship codes (GOLDM, SILVERMIC, CRUDEOILM, ...) over all turnover — how retail the commodity's book is. |
| `mcx_commodity_oi_value_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(open_interest_value_inr)` |  |  | Notional of open futures positions across every code and expiry, at the period's last session. A stock — never summed over days. |
| `mcx_commodity_option_notional_turnover_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(option_notional_turnover_inr)` |  |  | What MCX reports as option `Value` — (strike + premium) × quantity. Premium is the smaller number traders pay; this is the exposure that changed hands. |
| `mcx_commodity_option_premium_turnover_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(option_premium_turnover_inr)` |  |  | Premium actually paid across every option chain — MCX's notional `Value` less strike × quantity. |
| `mcx_commodity_parkinson_var_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(var_parkinson)` |  |  | Sessions With a Parkinson Reading — per Commodity |
| `mcx_commodity_parkinson_var_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(252 * var_parkinson)` |  |  | Parkinson Variance (component) — per Commodity |
| `mcx_commodity_parkinson_variance` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_parkinson_var_total / mcx_commodity_parkinson_var_days` |  |  | High–low range variance, (ln H/L)² ÷ 4 ln 2 per session, × 252. |
| `mcx_commodity_parkinson_vol` | derived | `fct_mcx_commodity_rollup_daily` | `derived` |  |  | Parkinson Volatility (annualised) — per Commodity |
| `mcx_commodity_period_return` | derived | `fct_mcx_commodity_rollup_daily` | `derived` |  |  | exp(Σ log return) − 1 over the query's window — compounding, not summing, daily returns. |
| `mcx_commodity_premium_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(premium_to_landed_pct)` |  |  | Sessions With a Parity Reading — per Commodity |
| `mcx_commodity_premium_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(premium_to_landed_pct)` |  |  | Landed-Parity Premium (component) — per Commodity |
| `mcx_commodity_put_call_ratio` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_put_oi_notional_inr / mcx_commodity_call_oi_notional_inr` |  |  | Put open interest over call, each weighted by its underlying's notional per lot so every code of the commodity counts at its size. Above ~1.3 put-heavy, below ~0.7 call-heavy. |
| `mcx_commodity_put_oi_notional_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(put_oi_notional_inr)` |  |  | Put Open Interest, Notional (component) — per Commodity |
| `mcx_commodity_realised_vol` | derived | `fct_mcx_commodity_rollup_daily` | `derived` |  |  | Realised Volatility, Close-to-Close (annualised) — per Commodity |
| `mcx_commodity_return_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(return_1d)` |  |  | Sessions With a Return — per Commodity |
| `mcx_commodity_return_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(return_1d)` |  |  | Daily Return (component) — per Commodity |
| `mcx_commodity_roll_yield_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(roll_yield_annualised)` |  |  | Sessions With a Roll Yield — per Commodity |
| `mcx_commodity_roll_yield_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(roll_yield_annualised)` |  |  | Roll Yield (component) — per Commodity |
| `mcx_commodity_rs_var_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(var_rogers_satchell)` |  |  | Sessions With a Rogers–Satchell Reading — per Commodity |
| `mcx_commodity_rs_var_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(252 * var_rogers_satchell)` |  |  | Rogers–Satchell Variance (component) — per Commodity |
| `mcx_commodity_rs_variance` | ratio | `fct_mcx_commodity_rollup_daily` | `mcx_commodity_rs_var_total / mcx_commodity_rs_var_days` |  |  | Rogers–Satchell (1991) drift-robust OHLC variance per session, × 252. Prefer it to Garman–Klass in a trending market. |
| `mcx_commodity_rs_vol` | derived | `fct_mcx_commodity_rollup_daily` | `derived` |  |  | Rogers–Satchell Volatility (annualised) — per Commodity |
| `mcx_commodity_rsi_days` | simple | `fct_mcx_commodity_rollup_daily` | `count(rsi_14)` |  |  | Sessions With an RSI Reading — per Commodity |
| `mcx_commodity_rsi_total` | simple | `fct_mcx_commodity_rollup_daily` | `sum(rsi_14)` |  |  | RSI (component) — per Commodity |
| `mcx_commodity_sessions` | simple | `fct_mcx_commodity_rollup_daily` | `count(commodity_day_id)` |  |  | Commodity-sessions on record; the denominator the per-session means divide by. |
| `mcx_commodity_turnover_inr` | simple | `fct_mcx_commodity_rollup_daily` | `sum(turnover_inr)` |  |  | Traded value of every code and expiry of the commodity, in rupees. Additive across commodities and days. |
| `mcx_commodity_turnover_mom` | derived | `fct_mcx_commodity_rollup_daily` | `derived` |  |  | Turnover, Month-on-Month Change — per Commodity |
| `mcx_commodity_up_sessions` | simple | `fct_mcx_commodity_rollup_daily` | `sum(is_up_session)` |  |  | Up Sessions — per Commodity |
| `mcx_commodity_volume_flagship_lots` | simple | `fct_mcx_commodity_rollup_daily` | `sum(volume_flagship_lots)` |  |  | Turnover restated in lots of the flagship contract, so GOLD, GOLDM and GOLDPETAL add up. Group by mcx_commodity — a gold lot is not a crude lot. |
| `mcx_contango_days` | simple | `fct_mcx_commodity_daily` | `sum(case when is_contango then 1 else 0 end)` |  |  | MCX Sessions in Contango |
| `mcx_contango_share` | ratio | `fct_mcx_commodity_daily` | `mcx_contango_days / mcx_session_days` |  |  | Contango sessions over all sessions. Group by contract_code. |
| `mcx_gk_vol_30d_days` | simple | `fct_mcx_commodity_daily` | `count(garman_klass_vol_30d)` |  |  | MCX Days With a Garman–Klass Reading |
| `mcx_gk_vol_30d_total` | simple | `fct_mcx_commodity_daily` | `sum(garman_klass_vol_30d)` |  |  | MCX Garman–Klass Vol 30d (component) |
| `mcx_parkinson_vol_30d_days` | simple | `fct_mcx_commodity_daily` | `count(parkinson_vol_30d)` |  |  | MCX Days With a Parkinson Reading |
| `mcx_parkinson_vol_30d_total` | simple | `fct_mcx_commodity_daily` | `sum(parkinson_vol_30d)` |  |  | MCX Parkinson Vol 30d (component) |
| `mcx_premium_days` | simple | `fct_mcx_commodity_daily` | `count(premium_to_landed_pct)` |  |  | MCX Days With a Parity Reading |
| `mcx_premium_total` | simple | `fct_mcx_commodity_daily` | `sum(premium_to_landed_pct)` |  |  | MCX Premium to Landed Parity (component) |
| `mcx_realised_vol_days` | simple | `fct_mcx_commodity_daily` | `count(realised_vol_20d)` |  |  | MCX Days With a Volatility Reading |
| `mcx_realised_vol_total` | simple | `fct_mcx_commodity_daily` | `sum(realised_vol_20d)` |  |  | MCX Realised Volatility (component) |
| `mcx_return_total` | simple | `fct_mcx_commodity_daily` | `sum(return_1d)` |  |  | MCX Summed Daily Return (component) |
| `mcx_roll_yield_days` | simple | `fct_mcx_commodity_daily` | `count(roll_yield_annualised)` |  |  | MCX Days With a Roll Yield |
| `mcx_roll_yield_total` | simple | `fct_mcx_commodity_daily` | `sum(roll_yield_annualised)` |  |  | MCX Roll Yield (component) |
| `mcx_rs_vol_30d_days` | simple | `fct_mcx_commodity_daily` | `count(rogers_satchell_vol_30d)` |  |  | MCX Days With a Rogers–Satchell Reading |
| `mcx_rs_vol_30d_total` | simple | `fct_mcx_commodity_daily` | `sum(rogers_satchell_vol_30d)` |  |  | MCX Rogers–Satchell Vol 30d (component) |
| `mcx_rsi_days` | simple | `fct_mcx_commodity_daily` | `count(rsi_14)` |  |  | MCX Days With an RSI Reading |
| `mcx_rsi_total` | simple | `fct_mcx_commodity_daily` | `sum(rsi_14)` |  |  | MCX RSI (component) |
| `mcx_session_days` | simple | `fct_mcx_commodity_daily` | `count(continuous_id)` |  |  | Code-sessions on record. The denominator the means below divide by. |
| `mcx_turnover_inr` | simple | `fct_mcx_commodity_daily` | `sum(turnover_inr)` |  |  | Traded value across every expiry, in rupees. Additive across codes and days. |
| `mcx_volume_lots` | simple | `fct_mcx_commodity_daily` | `sum(volume_lots)` |  |  | Lots traded across every expiry. Additive within a code; a GOLD lot is not a GOLDPETAL lot, so compare across codes with turnover instead. |
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
