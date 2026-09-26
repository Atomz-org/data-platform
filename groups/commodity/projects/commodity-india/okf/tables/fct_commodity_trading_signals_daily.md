---
type: Table
title: fct_commodity_trading_signals_daily
description: Timing signals on the USD benchmark — where a price sits in its own recent
  history, not what it costs. Every measure is unit-free, so unlike the price itself
  these are safe to compare across commodities.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per price date
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_commodity_trading_signals_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `close_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `currency_code` | VARCHAR |  | — | 0.00 |
| `high_252d` | DOUBLE |  | — | 0.00 |
| `is_latest` | BOOLEAN |  | — | 0.00 |
| `low_252d` | DOUBLE |  | — | 0.00 |
| `ma_crossover` | VARCHAR |  | — | 0.00 |
| `ma_gap_50d_pct` | DOUBLE |  | — | 0.00 |
| `ma_regime` | VARCHAR |  | — | 0.00 |
| `momentum_20d_pct` | DOUBLE |  | — | 0.00 |
| `moving_avg_20d` | DOUBLE |  | — | 0.00 |
| `moving_avg_50d` | DOUBLE |  | — | 0.00 |
| `pct_of_52w_range` | DOUBLE |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_change_pct` | DOUBLE |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `realised_vol_20d` | DOUBLE |  | — | 0.00 |
| `stance` | VARCHAR |  | — | 0.00 |
| `volatility_regime` | VARCHAR |  | — | 0.00 |
| `z_score_60d` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [avg_momentum_20d](/metrics/avg_momentum_20d.md)
* [avg_range_position](/metrics/avg_range_position.md)
* [avg_realised_vol](/metrics/avg_realised_vol.md)
* [momentum_20d_days](/metrics/momentum_20d_days.md)
* [momentum_20d_total](/metrics/momentum_20d_total.md)
* [range_position_days](/metrics/range_position_days.md)
* [range_position_total](/metrics/range_position_total.md)
* [realised_vol_days](/metrics/realised_vol_days.md)
* [realised_vol_total](/metrics/realised_vol_total.md)
* [signal_days](/metrics/signal_days.md)

# Lineage

* **Upstream:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Read by:** `report_buy_sell_signals` (data-platform), `report_index` (data-platform), `report_metrics_avg_momentum_20d` (data-platform), `report_metrics_avg_range_position` (data-platform), `report_metrics_avg_realised_vol` (data-platform), `report_metrics_momentum_20d_days` (data-platform), and 6 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
