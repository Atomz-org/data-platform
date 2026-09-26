---
type: Table
title: fct_mcx_commodity_daily
description: 'The continuous most-active MCX series per contract code with every trading
  metric: returns (1d–252d, YTD), SMA 20/50/200, EMA/MACD, RSI(14), ATR(14), Bollinger(20,2),
  52-week range and drawdown, realised and Parkinson volatility, OI build-up across
  expiries, calendar spread, annualised carry, rollover, premium to landed import
  parity, and a legible stance. Indicators run on roll-free back-adjusted prices and
  are null until their window is full. Prices non-additive: aggregate within one contract_code.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: ContractSession
okf_x_layer: marts
okf_x_grain: one MCX contract code per trading day
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_mcx_commodity_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `active_contract_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_mcx_contracts](/tables/dim_mcx_contracts.md) | 1.00 |
| `active_expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `adj_close_price` | DOUBLE |  | — | 0.00 |
| `annualised_carry` | DOUBLE |  | — | 0.00 |
| `atr_14` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `atr_14_pct` | DOUBLE |  | — | 0.00 |
| `bollinger_bandwidth` | DOUBLE |  | — | 0.00 |
| `bollinger_lower` | DOUBLE |  | — | 0.00 |
| `bollinger_pct_b` | DOUBLE |  | — | 0.00 |
| `bollinger_upper` | DOUBLE |  | — | 0.00 |
| `calendar_spread` | DOUBLE |  | — | 0.00 |
| `close_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `close_vol_14d` | DOUBLE |  | — | 0.00 |
| `close_vol_30d` | DOUBLE |  | — | 0.00 |
| `close_vol_90d` | DOUBLE |  | — | 0.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `continuous_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `contract_code` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `cumulative_return` | DOUBLE |  | — | 0.00 |
| `curve_state` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `days_to_expiry` | BIGINT |  | — | 0.00 |
| `drawdown_from_52w_peak` | DOUBLE |  | — | 0.00 |
| `ema_12` | DOUBLE |  | — | 0.00 |
| `ema_200` | DOUBLE |  | — | 0.00 |
| `ema_200_trend` | VARCHAR |  | — | 0.00 |
| `ema_21` | DOUBLE |  | — | 0.00 |
| `ema_26` | DOUBLE |  | — | 0.00 |
| `ema_9` | DOUBLE |  | — | 0.00 |
| `ema_9_21_signal` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `garman_klass_vol_14d` | DOUBLE |  | — | 0.00 |
| `garman_klass_vol_30d` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `garman_klass_vol_90d` | DOUBLE |  | — | 0.00 |
| `high_52w` | DOUBLE |  | — | 0.00 |
| `high_price` | DOUBLE |  | — | 0.00 |
| `is_backwardation` | BOOLEAN | flag | A true/false state of the row (prohibited, confirmed). Passes through staging; never aggregated. | 1.00 |
| `is_contango` | BOOLEAN | flag | A true/false state of the row (prohibited, confirmed). Passes through staging; never aggregated. | 1.00 |
| `is_flagship` | BOOLEAN |  | — | 0.00 |
| `is_latest` | BOOLEAN | flag | A true/false state of the row (prohibited, confirmed). Passes through staging; never aggregated. | 1.00 |
| `is_liquid` | BOOLEAN |  | — | 0.00 |
| `is_roll_day` | BOOLEAN |  | — | 0.00 |
| `is_traded` | BOOLEAN |  | — | 0.00 |
| `landed_parity_price` | DECIMAL |  | — | 0.00 |
| `log_return_1d` | DOUBLE |  | — | 0.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `low_52w` | DOUBLE |  | — | 0.00 |
| `low_price` | DOUBLE |  | — | 0.00 |
| `ma_crossover` | VARCHAR |  | — | 0.00 |
| `macd_crossover` | VARCHAR |  | — | 0.00 |
| `macd_histogram_pct` | DOUBLE |  | — | 0.00 |
| `macd_line_pct` | DOUBLE |  | — | 0.00 |
| `macd_signal_pct` | DOUBLE |  | — | 0.00 |
| `mcx_commodity` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `near_close_price` | DOUBLE |  | — | 0.00 |
| `near_expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `next_close_price` | DOUBLE |  | — | 0.00 |
| `next_expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `notional_per_lot_inr` | DOUBLE |  | — | 0.00 |
| `oi_buildup` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `open_expiries` | BIGINT |  | — | 0.00 |
| `open_interest_change_lots` | VARCHAR |  | — | 0.00 |
| `open_interest_change_pct` | DOUBLE |  | — | 0.00 |
| `open_interest_lots` | BIGINT | quantity | Countable measure. | 1.00 |
| `open_interest_value_inr` | DOUBLE |  | — | 0.00 |
| `open_price` | DOUBLE |  | — | 0.00 |
| `parkinson_vol_14d` | DOUBLE |  | — | 0.00 |
| `parkinson_vol_20d` | DOUBLE |  | — | 0.00 |
| `parkinson_vol_30d` | DOUBLE |  | — | 0.00 |
| `parkinson_vol_90d` | DOUBLE |  | — | 0.00 |
| `premium_to_landed_pct` | DOUBLE |  | — | 0.00 |
| `previous_close_price` | DOUBLE |  | — | 0.00 |
| `price_change` | DOUBLE |  | — | 0.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `quote_units_per_lot` | DOUBLE |  | — | 0.00 |
| `range_position_52w` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `realised_vol_20d` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `relative_volume_20d` | DOUBLE |  | — | 0.00 |
| `return_1d` | DOUBLE |  | — | 0.00 |
| `return_21d` | DOUBLE |  | — | 0.00 |
| `return_252d` | DOUBLE |  | — | 0.00 |
| `return_5d` | DOUBLE |  | — | 0.00 |
| `return_63d` | DOUBLE |  | — | 0.00 |
| `return_ytd` | DOUBLE |  | — | 0.00 |
| `rogers_satchell_vol_14d` | DOUBLE |  | — | 0.00 |
| `rogers_satchell_vol_30d` | DOUBLE |  | — | 0.00 |
| `rogers_satchell_vol_90d` | DOUBLE |  | — | 0.00 |
| `roll_yield_annualised` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `rollover_pct` | DOUBLE |  | — | 0.00 |
| `rsi_14` | DOUBLE |  | — | 0.00 |
| `rsi_state` | VARCHAR |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `session_number` | BIGINT |  | — | 0.00 |
| `sma_20` | DOUBLE |  | — | 0.00 |
| `sma_200` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `sma_50` | DOUBLE |  | — | 0.00 |
| `stance` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `trade_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `trend_regime` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `turnover_inr` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `var_garman_klass` | DOUBLE |  | — | 0.00 |
| `var_parkinson` | DOUBLE |  | — | 0.00 |
| `var_rogers_satchell` | DOUBLE |  | — | 0.00 |
| `volatility_regime` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `volume_lots` | BIGINT | quantity | Countable measure. | 1.00 |

# Concept

Instantiates [ContractSession](/concepts/ContractSession.md).

# Metrics

* [avg_mcx_daily_return](/metrics/avg_mcx_daily_return.md)
* [avg_mcx_garman_klass_vol_30d](/metrics/avg_mcx_garman_klass_vol_30d.md)
* [avg_mcx_parkinson_vol_30d](/metrics/avg_mcx_parkinson_vol_30d.md)
* [avg_mcx_premium_to_landed](/metrics/avg_mcx_premium_to_landed.md)
* [avg_mcx_realised_vol](/metrics/avg_mcx_realised_vol.md)
* [avg_mcx_rogers_satchell_vol_30d](/metrics/avg_mcx_rogers_satchell_vol_30d.md)
* [avg_mcx_roll_yield](/metrics/avg_mcx_roll_yield.md)
* [avg_mcx_rsi](/metrics/avg_mcx_rsi.md)
* [mcx_backwardation_days](/metrics/mcx_backwardation_days.md)
* [mcx_contango_days](/metrics/mcx_contango_days.md)
* [mcx_contango_share](/metrics/mcx_contango_share.md)
* [mcx_gk_vol_30d_days](/metrics/mcx_gk_vol_30d_days.md)
* [mcx_gk_vol_30d_total](/metrics/mcx_gk_vol_30d_total.md)
* [mcx_parkinson_vol_30d_days](/metrics/mcx_parkinson_vol_30d_days.md)
* [mcx_parkinson_vol_30d_total](/metrics/mcx_parkinson_vol_30d_total.md)
* [mcx_premium_days](/metrics/mcx_premium_days.md)
* [mcx_premium_total](/metrics/mcx_premium_total.md)
* [mcx_realised_vol_days](/metrics/mcx_realised_vol_days.md)
* [mcx_realised_vol_total](/metrics/mcx_realised_vol_total.md)
* [mcx_return_total](/metrics/mcx_return_total.md)
* [mcx_roll_yield_days](/metrics/mcx_roll_yield_days.md)
* [mcx_roll_yield_total](/metrics/mcx_roll_yield_total.md)
* [mcx_rs_vol_30d_days](/metrics/mcx_rs_vol_30d_days.md)
* [mcx_rs_vol_30d_total](/metrics/mcx_rs_vol_30d_total.md)
* [mcx_rsi_days](/metrics/mcx_rsi_days.md)
* [mcx_rsi_total](/metrics/mcx_rsi_total.md)
* [mcx_session_days](/metrics/mcx_session_days.md)
* [mcx_turnover_inr](/metrics/mcx_turnover_inr.md)
* [mcx_volume_lots](/metrics/mcx_volume_lots.md)

# Lineage

* **Upstream:** [fct_mcx_lot_equivalents_daily](/tables/fct_mcx_lot_equivalents_daily.md), `int_mcx__continuous_daily`, `int_mcx__smoothed_indicators`
* **Downstream:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md), [rpt_mcx_commodity_board](/tables/rpt_mcx_commodity_board.md)
* **Read by:** `report_mcx_[commodity]` (data-platform), `report_mcx_index` (data-platform), `report_metrics_avg_mcx_daily_return` (data-platform), `report_metrics_avg_mcx_garman_klass_vol_30d` (data-platform), `report_metrics_avg_mcx_parkinson_vol_30d` (data-platform), `report_metrics_avg_mcx_premium_to_landed` (data-platform), and 25 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
* **Decision** ADR-0006 — MCX's own bhavcopy lands as one dlt pipeline per commodity (accepted)
