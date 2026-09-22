---
type: Table
title: fct_market_spreads_daily
description: 'On days at least two markets priced a commodity: each market''s landed
  price in USD per quote unit against the cheapest market''s, as a spread and a percentage.
  Pure market effects — duty regimes and FX timing — because both sides stand on the
  same benchmark.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per market per price date
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_market_spreads_daily
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `cheapest_landed_usd` | DECIMAL |  | — | 0.00 |
| `cheapest_market_code` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_markets](/tables/dim_markets.md) | 1.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `is_cheapest_market` | BOOLEAN |  | — | 0.00 |
| `landed_price_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `landed_price_usd_per_quote_unit` | DECIMAL |  | — | 0.00 |
| `market_code` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_markets](/tables/dim_markets.md) | 1.00 |
| `markets_compared` | BIGINT |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `spread_to_cheapest_pct` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `spread_to_cheapest_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).

# Metrics

* [avg_spread_to_cheapest_ratio](/metrics/avg_spread_to_cheapest_ratio.md)
* [avg_spread_to_cheapest_usd](/metrics/avg_spread_to_cheapest_usd.md)
* [cheapest_usd_total](/metrics/cheapest_usd_total.md)
* [days_as_cheapest_market](/metrics/days_as_cheapest_market.md)
* [spread_days](/metrics/spread_days.md)
* [spread_usd_total](/metrics/spread_usd_total.md)

# Lineage

* **Upstream:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Downstream:** [rpt_market_comparison_board](/tables/rpt_market_comparison_board.md)
* **Read by:** `report_index` (data-platform), `report_metrics_avg_spread_to_cheapest_ratio` (data-platform), `report_metrics_avg_spread_to_cheapest_usd` (data-platform), `report_metrics_cheapest_usd_total` (data-platform), `report_metrics_days_as_cheapest_market` (data-platform), `report_metrics_spread_days` (data-platform), and 1 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
