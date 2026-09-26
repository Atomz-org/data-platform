---
type: Table
title: rpt_mcx_commodity_board
description: 'One row per MCX contract code: its latest session''s price, returns,
  trend, momentum, volatility, positioning, curve, parity premium and stance, with
  the nearest option chain''s put/call ratio and max pain. The table behind the MCX
  summary page and each commodity page''s headline.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one MCX contract code
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_mcx_commodity_board
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `active_contract_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `active_expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `annualised_carry` | DOUBLE |  | — | 0.00 |
| `atr_14` | DOUBLE |  | — | 0.00 |
| `atr_14_pct` | DOUBLE |  | — | 0.00 |
| `bollinger_pct_b` | DOUBLE |  | — | 0.00 |
| `calendar_spread` | DOUBLE |  | — | 0.00 |
| `call_wall_strike` | DOUBLE |  | — | 0.00 |
| `close_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `close_vol_30d` | DOUBLE |  | — | 0.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `contract_code` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `contract_name` | VARCHAR |  | — | 0.00 |
| `cumulative_return` | DOUBLE |  | — | 0.00 |
| `curve_state` | VARCHAR |  | — | 0.00 |
| `days_to_expiry` | BIGINT |  | — | 0.00 |
| `drawdown_from_52w_peak` | DOUBLE |  | — | 0.00 |
| `ema_200` | DOUBLE |  | — | 0.00 |
| `ema_200_trend` | VARCHAR |  | — | 0.00 |
| `ema_21` | DOUBLE |  | — | 0.00 |
| `ema_9` | DOUBLE |  | — | 0.00 |
| `ema_9_21_signal` | VARCHAR |  | — | 0.00 |
| `garman_klass_vol_30d` | DOUBLE |  | — | 0.00 |
| `high_52w` | DOUBLE |  | — | 0.00 |
| `is_backwardation` | BOOLEAN |  | — | 0.00 |
| `is_contango` | BOOLEAN |  | — | 0.00 |
| `is_flagship` | BOOLEAN |  | — | 0.00 |
| `is_liquid` | BOOLEAN |  | — | 0.00 |
| `is_stale` | BOOLEAN | flag | A true/false state of the row (prohibited, confirmed). Passes through staging; never aggregated. | 1.00 |
| `landed_parity_price` | DECIMAL |  | — | 0.00 |
| `latest_trade_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `lot_size` | DOUBLE |  | — | 0.00 |
| `lot_unit` | VARCHAR |  | — | 0.00 |
| `low_52w` | DOUBLE |  | — | 0.00 |
| `ma_crossover` | VARCHAR |  | — | 0.00 |
| `macd_crossover` | VARCHAR |  | — | 0.00 |
| `macd_histogram_pct` | DOUBLE |  | — | 0.00 |
| `max_pain_distance_pct` | DOUBLE |  | — | 0.00 |
| `max_pain_strike` | DOUBLE |  | — | 0.00 |
| `mcx_commodity` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `notional_per_lot_inr` | DOUBLE |  | — | 0.00 |
| `oi_buildup` | VARCHAR |  | — | 0.00 |
| `open_interest_change_pct` | DOUBLE |  | — | 0.00 |
| `open_interest_lots` | VARCHAR |  | — | 0.00 |
| `open_interest_value_inr` | DOUBLE |  | — | 0.00 |
| `option_expiry_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `option_positioning` | VARCHAR |  | — | 0.00 |
| `parkinson_vol_20d` | DOUBLE |  | — | 0.00 |
| `parkinson_vol_30d` | DOUBLE |  | — | 0.00 |
| `premium_to_landed_pct` | DOUBLE |  | — | 0.00 |
| `price_change` | DOUBLE |  | — | 0.00 |
| `put_call_ratio_oi` | DOUBLE |  | — | 0.00 |
| `put_call_ratio_volume` | DOUBLE |  | — | 0.00 |
| `put_wall_strike` | DOUBLE |  | — | 0.00 |
| `quote_size` | DOUBLE |  | — | 0.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `range_position_52w` | DOUBLE |  | — | 0.00 |
| `realised_vol_20d` | DOUBLE |  | — | 0.00 |
| `relative_volume_20d` | DOUBLE |  | — | 0.00 |
| `return_1d` | DOUBLE |  | — | 0.00 |
| `return_21d` | DOUBLE |  | — | 0.00 |
| `return_252d` | DOUBLE |  | — | 0.00 |
| `return_5d` | DOUBLE |  | — | 0.00 |
| `return_63d` | DOUBLE |  | — | 0.00 |
| `return_ytd` | DOUBLE |  | — | 0.00 |
| `rogers_satchell_vol_30d` | DOUBLE |  | — | 0.00 |
| `roll_yield_annualised` | DOUBLE |  | — | 0.00 |
| `rollover_pct` | DOUBLE |  | — | 0.00 |
| `rsi_14` | DOUBLE |  | — | 0.00 |
| `rsi_state` | VARCHAR |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `sessions_behind_days` | BIGINT |  | — | 0.00 |
| `sma_200` | DOUBLE |  | — | 0.00 |
| `sma_50` | DOUBLE |  | — | 0.00 |
| `stance` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `trend_regime` | VARCHAR |  | — | 0.00 |
| `turnover_inr` | DECIMAL |  | — | 0.00 |
| `volatility_regime` | VARCHAR |  | — | 0.00 |
| `volume_lots` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Lineage

* **Upstream:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md), [fct_mcx_options_daily](/tables/fct_mcx_options_daily.md)
* **Read by:** `report_mcx_[commodity]` (data-platform), `report_mcx_index` (data-platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
