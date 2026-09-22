---
type: Table
title: rpt_market_comparison_board
description: 'One row per commodity per market: the latest landed price on the benchmark''s
  footing, the cheapest market to land it in, each market''s spread to it, and how
  old each market''s number is. The table behind the market comparison board.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: PriceObservation
okf_x_layer: marts
okf_x_grain: one commodity per market
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `benchmark_price_usd` | DOUBLE |  | — | 0.00 |
| `board_row_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `category` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `cheapest_landed_usd` | DECIMAL |  | — | 0.00 |
| `cheapest_market_code` | VARCHAR |  | — | 0.00 |
| `commodity_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_commodities](/tables/dim_commodities.md) | 1.00 |
| `commodity_name` | VARCHAR |  | — | 0.00 |
| `currency_code` | VARCHAR |  | — | 0.00 |
| `effective_duty_rate` | DECIMAL |  | — | 0.00 |
| `import_parity_premium_pct` | DOUBLE |  | — | 0.00 |
| `is_cheapest_market` | BOOLEAN |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `is_import_prohibited` | BOOLEAN |  | — | 0.00 |
| `is_stale` | BOOLEAN |  | — | 0.00 |
| `landed_price_local` | DECIMAL |  | — | 0.00 |
| `landed_price_usd_per_quote_unit` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `market_code` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_markets](/tables/dim_markets.md) | 1.00 |
| `market_name` | VARCHAR |  | — | 0.00 |
| `market_unit` | VARCHAR |  | — | 0.00 |
| `markets_compared` | BIGINT |  | — | 0.00 |
| `price_age_days` | BIGINT |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `spread_to_cheapest_pct` | DECIMAL | rate_fraction | A proportion stored as a fraction — 0.15 means 15%. | 1.00 |
| `usd_fx_rate` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [PriceObservation](/concepts/PriceObservation.md).
