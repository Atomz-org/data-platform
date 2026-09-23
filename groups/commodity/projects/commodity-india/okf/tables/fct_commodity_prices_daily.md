---
type: Table
title: fct_commodity_prices_daily
description: 'Daily benchmark price per commodity in USD per quote unit, with day-on-day
  change, 20/50-day moving averages and a 252-trading-day range. Prices are non-additive:
  aggregate within one commodity only.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per price date
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_commodity_prices_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `close_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `high_252d` | DOUBLE |  | — | 0.00 |
| `high_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `is_latest` | BOOLEAN |  | — | 0.00 |
| `low_252d` | DOUBLE |  | — | 0.00 |
| `low_price` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `moving_avg_20d` | DOUBLE |  | — | 0.00 |
| `moving_avg_50d` | DOUBLE |  | — | 0.00 |
| `open_price` | DOUBLE |  | — | 0.00 |
| `prev_close_price` | DOUBLE |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_change` | DOUBLE |  | — | 0.00 |
| `price_change_pct` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `volume` | BIGINT | quantity | Countable measure. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [avg_benchmark_price_usd](/metrics/avg_benchmark_price_usd.md)
* [benchmark_price_days](/metrics/benchmark_price_days.md)
* [benchmark_price_mom_change](/metrics/benchmark_price_mom_change.md)
* [benchmark_price_usd_total](/metrics/benchmark_price_usd_total.md)
* [contracts_traded](/metrics/contracts_traded.md)
* [period_high_price_usd](/metrics/period_high_price_usd.md)
* [period_low_price_usd](/metrics/period_low_price_usd.md)

# Lineage

* **Upstream:** `int_commodity_prices__usd`
* **Downstream:** [rpt_commodity_price_board](/tables/rpt_commodity_price_board.md)
* **Read by:** `commodity_price_board` (Commodity Research), `report_index` (data-platform), `report_landed_cost` (data-platform), `report_metrics_avg_benchmark_price_usd` (data-platform), `report_metrics_benchmark_price_days` (data-platform), `report_metrics_benchmark_price_usd_total` (data-platform), and 3 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
