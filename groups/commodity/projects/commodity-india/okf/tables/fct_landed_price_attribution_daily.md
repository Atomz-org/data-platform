---
type: Table
title: fct_landed_price_attribution_daily
description: Why the landed rupee price moved over 20 trading days, split into the
  benchmark, the rupee and duty. An Indian buyer decides on landed rupees, and a USD-only
  signal cannot tell a commodity move from a currency move — which is the difference
  between a buying decision and a treasury one.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per price date
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_landed_price_attribution_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `benchmark_20d_ago` | DOUBLE |  | — | 0.00 |
| `benchmark_contribution_pct` | DOUBLE |  | — | 0.00 |
| `benchmark_usd_per_market_unit` | DOUBLE |  | — | 0.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `duty_contribution_pct` | DOUBLE |  | — | 0.00 |
| `duty_rate_20d_ago` | DECIMAL |  | — | 0.00 |
| `effective_duty_rate` | DECIMAL |  | — | 0.00 |
| `fx_20d_ago` | DOUBLE |  | — | 0.00 |
| `fx_contribution_pct` | DOUBLE |  | — | 0.00 |
| `fx_share_of_move` | DOUBLE |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `is_import_prohibited` | BOOLEAN |  | — | 0.00 |
| `is_latest` | BOOLEAN |  | — | 0.00 |
| `landed_change_20d_pct` | DOUBLE |  | — | 0.00 |
| `landed_price_local` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `landed_price_local_20d_ago` | DECIMAL |  | — | 0.00 |
| `market_code` | VARCHAR | geo_country | ISO 3166 country code. | 1.00 |
| `market_unit` | VARCHAR |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `primary_driver` | VARCHAR |  | — | 0.00 |
| `usd_fx_rate` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [attribution_days](/metrics/attribution_days.md)
* [avg_fx_share_of_move](/metrics/avg_fx_share_of_move.md)
* [benchmark_contribution_total](/metrics/benchmark_contribution_total.md)
* [duty_contribution_total](/metrics/duty_contribution_total.md)
* [fx_contribution_total](/metrics/fx_contribution_total.md)
* [fx_share_days](/metrics/fx_share_days.md)
* [fx_share_total](/metrics/fx_share_total.md)

# Lineage

* **Upstream:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Read by:** `report_metrics_attribution_days` (data-platform), `report_metrics_avg_fx_share_of_move` (data-platform), `report_metrics_benchmark_contribution_total` (data-platform), `report_metrics_duty_contribution_total` (data-platform), `report_metrics_fx_contribution_total` (data-platform), `report_metrics_fx_share_days` (data-platform), and 1 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
