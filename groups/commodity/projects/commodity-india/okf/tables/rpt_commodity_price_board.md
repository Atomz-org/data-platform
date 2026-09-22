---
type: Table
title: rpt_commodity_price_board
description: 'One row per tracked commodity: latest benchmark and move, 252-day range,
  landed price in this market''s currency, duty, precious-metal spot basis, and staleness.
  The table behind the commodity price board.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Commodity
okf_x_layer: marts
okf_x_grain: one commodity
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_commodity_price_board
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `benchmark_price_usd` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `category` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `commodity_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `commodity_name` | VARCHAR |  | — | 0.00 |
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `duty_basis` | VARCHAR |  | — | 0.00 |
| `effective_duty_rate` | DECIMAL |  | — | 0.00 |
| `exchange` | VARCHAR |  | — | 0.00 |
| `futures_spot_basis_pct` | DOUBLE |  | — | 0.00 |
| `high_252d` | DOUBLE |  | — | 0.00 |
| `is_duty_rate_confirmed` | BOOLEAN |  | — | 0.00 |
| `is_import_prohibited` | BOOLEAN |  | — | 0.00 |
| `is_stale` | BOOLEAN |  | — | 0.00 |
| `landed_price_change_pct` | DOUBLE |  | — | 0.00 |
| `landed_price_inr` | DECIMAL |  | — | 0.00 |
| `landed_price_local` | DECIMAL | unit_price | Price of one unit of measure. Non-additive — never summed across rows. Qualified by a sibling currency_code and a unit_of_measure. | 1.00 |
| `low_252d` | DOUBLE |  | — | 0.00 |
| `market_code` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `market_unit` | VARCHAR |  | — | 0.00 |
| `price_age_days` | BIGINT |  | — | 0.00 |
| `price_basis` | VARCHAR |  | — | 0.00 |
| `price_change_pct` | DOUBLE |  | — | 0.00 |
| `price_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `quote_unit` | VARCHAR |  | — | 0.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `spot_price_usd` | DOUBLE |  | — | 0.00 |
| `spot_quoted_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `usd_fx_rate` | DECIMAL | exchange_rate | Units of quote currency per one unit of base currency. | 1.00 |
| `usd_inr_rate` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Commodity](/concepts/Commodity.md).

# Lineage

* **Upstream:** [dim_commodities](/tables/dim_commodities.md), [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md), [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md), `stg_gold_api__spot_prices`
* **Read by:** `commodity_price_board` (Commodity Research), `report_landed_cost` (data-platform), `report_price_board` (data-platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
