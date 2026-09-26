---
type: Table
title: fct_mcx_commodity_rollup_daily
description: 'One MCX commodity per session (gold, not its five codes): the flagship''s
  price, return, per-session variances under four estimators, momentum, curve and
  parity, with turnover, open-interest value and notional-weighted option open interest
  summed across every code and expiry. The fact the per-commodity semantic model `mcx_commodities`
  reads.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one MCX commodity per trading day
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_mcx_commodity_rollup_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `call_oi_notional_inr` | DOUBLE |  | — | 0.00 |
| `codes_trading` | BIGINT |  | — | 0.00 |
| `commodity_day_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `flagship_close_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `flagship_contract_code` | VARCHAR |  | — | 0.00 |
| `garman_klass_vol_30d` | DOUBLE |  | — | 0.00 |
| `is_backwardation_session` | INTEGER |  | — | 0.00 |
| `is_contango_session` | INTEGER |  | — | 0.00 |
| `is_latest` | BOOLEAN |  | — | 0.00 |
| `is_liquid` | BOOLEAN |  | — | 0.00 |
| `is_up_session` | INTEGER |  | — | 0.00 |
| `log_return_1d` | DOUBLE |  | — | 0.00 |
| `mcx_commodity` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `mini_turnover_inr` | DECIMAL |  | — | 0.00 |
| `open_interest_value_inr` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `option_notional_turnover_inr` | DECIMAL |  | — | 0.00 |
| `option_premium_turnover_inr` | DOUBLE |  | — | 0.00 |
| `premium_to_landed_pct` | DOUBLE |  | — | 0.00 |
| `put_oi_notional_inr` | DOUBLE |  | — | 0.00 |
| `return_1d` | DOUBLE |  | — | 0.00 |
| `roll_yield_annualised` | DOUBLE |  | — | 0.00 |
| `rsi_14` | DOUBLE |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `sq_log_return_1d` | DOUBLE |  | — | 0.00 |
| `stance` | VARCHAR |  | — | 0.00 |
| `trade_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `trend_regime` | VARCHAR |  | — | 0.00 |
| `turnover_inr` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `var_garman_klass` | DOUBLE |  | — | 0.00 |
| `var_parkinson` | DOUBLE |  | — | 0.00 |
| `var_rogers_satchell` | DOUBLE |  | — | 0.00 |
| `volatility_regime` | VARCHAR |  | — | 0.00 |
| `volume_flagship_lots` | BIGINT | quantity | Countable measure. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [mcx_commodity_avg_daily_return](/metrics/mcx_commodity_avg_daily_return.md)
* [mcx_commodity_avg_premium_to_landed](/metrics/mcx_commodity_avg_premium_to_landed.md)
* [mcx_commodity_avg_roll_yield](/metrics/mcx_commodity_avg_roll_yield.md)
* [mcx_commodity_avg_rsi](/metrics/mcx_commodity_avg_rsi.md)
* [mcx_commodity_backwardation_sessions](/metrics/mcx_commodity_backwardation_sessions.md)
* [mcx_commodity_backwardation_share](/metrics/mcx_commodity_backwardation_share.md)
* [mcx_commodity_call_oi_notional_inr](/metrics/mcx_commodity_call_oi_notional_inr.md)
* [mcx_commodity_close_var_days](/metrics/mcx_commodity_close_var_days.md)
* [mcx_commodity_close_var_total](/metrics/mcx_commodity_close_var_total.md)
* [mcx_commodity_close_variance](/metrics/mcx_commodity_close_variance.md)
* [mcx_commodity_contango_sessions](/metrics/mcx_commodity_contango_sessions.md)
* [mcx_commodity_contango_share](/metrics/mcx_commodity_contango_share.md)
* [mcx_commodity_gk_var_days](/metrics/mcx_commodity_gk_var_days.md)
* [mcx_commodity_gk_var_total](/metrics/mcx_commodity_gk_var_total.md)
* [mcx_commodity_gk_variance](/metrics/mcx_commodity_gk_variance.md)
* [mcx_commodity_gk_vol](/metrics/mcx_commodity_gk_vol.md)
* [mcx_commodity_hit_rate](/metrics/mcx_commodity_hit_rate.md)
* [mcx_commodity_log_return](/metrics/mcx_commodity_log_return.md)
* [mcx_commodity_mini_turnover_inr](/metrics/mcx_commodity_mini_turnover_inr.md)
* [mcx_commodity_mini_turnover_share](/metrics/mcx_commodity_mini_turnover_share.md)
* [mcx_commodity_oi_value_inr](/metrics/mcx_commodity_oi_value_inr.md)
* [mcx_commodity_option_notional_turnover_inr](/metrics/mcx_commodity_option_notional_turnover_inr.md)
* [mcx_commodity_option_premium_turnover_inr](/metrics/mcx_commodity_option_premium_turnover_inr.md)
* [mcx_commodity_parkinson_var_days](/metrics/mcx_commodity_parkinson_var_days.md)
* [mcx_commodity_parkinson_var_total](/metrics/mcx_commodity_parkinson_var_total.md)
* [mcx_commodity_parkinson_variance](/metrics/mcx_commodity_parkinson_variance.md)
* [mcx_commodity_parkinson_vol](/metrics/mcx_commodity_parkinson_vol.md)
* [mcx_commodity_period_return](/metrics/mcx_commodity_period_return.md)
* [mcx_commodity_premium_days](/metrics/mcx_commodity_premium_days.md)
* [mcx_commodity_premium_total](/metrics/mcx_commodity_premium_total.md)
* [mcx_commodity_put_call_ratio](/metrics/mcx_commodity_put_call_ratio.md)
* [mcx_commodity_put_oi_notional_inr](/metrics/mcx_commodity_put_oi_notional_inr.md)
* [mcx_commodity_realised_vol](/metrics/mcx_commodity_realised_vol.md)
* [mcx_commodity_return_days](/metrics/mcx_commodity_return_days.md)
* [mcx_commodity_return_total](/metrics/mcx_commodity_return_total.md)
* [mcx_commodity_roll_yield_days](/metrics/mcx_commodity_roll_yield_days.md)
* [mcx_commodity_roll_yield_total](/metrics/mcx_commodity_roll_yield_total.md)
* [mcx_commodity_rs_var_days](/metrics/mcx_commodity_rs_var_days.md)
* [mcx_commodity_rs_var_total](/metrics/mcx_commodity_rs_var_total.md)
* [mcx_commodity_rs_variance](/metrics/mcx_commodity_rs_variance.md)
* [mcx_commodity_rs_vol](/metrics/mcx_commodity_rs_vol.md)
* [mcx_commodity_rsi_days](/metrics/mcx_commodity_rsi_days.md)
* [mcx_commodity_rsi_total](/metrics/mcx_commodity_rsi_total.md)
* [mcx_commodity_sessions](/metrics/mcx_commodity_sessions.md)
* [mcx_commodity_turnover_inr](/metrics/mcx_commodity_turnover_inr.md)
* [mcx_commodity_turnover_mom](/metrics/mcx_commodity_turnover_mom.md)
* [mcx_commodity_up_sessions](/metrics/mcx_commodity_up_sessions.md)
* [mcx_commodity_volume_flagship_lots](/metrics/mcx_commodity_volume_flagship_lots.md)

# Lineage

* **Upstream:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md), [fct_mcx_options_daily](/tables/fct_mcx_options_daily.md)
* **Read by:** `report_mcx_metrics` (data-platform), `report_metrics_mcx_commodity_avg_daily_return` (data-platform), `report_metrics_mcx_commodity_avg_premium_to_landed` (data-platform), `report_metrics_mcx_commodity_avg_roll_yield` (data-platform), `report_metrics_mcx_commodity_avg_rsi` (data-platform), `report_metrics_mcx_commodity_backwardation_sessions` (data-platform), and 37 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
