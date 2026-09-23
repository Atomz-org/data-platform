---
type: Table
title: dim_commodities
description: The group catalog as every market sees it, with how many markets currently
  price each commodity.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Commodity
okf_x_layer: marts
okf_x_grain: one commodity
okf_x_columns_withheld: 0
okf_x_kg_node: model:dim_commodities
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `category` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `commodity_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `commodity_name` | VARCHAR |  | — | 0.00 |
| `exchange` | VARCHAR |  | — | 0.00 |
| `markets_pricing` | BIGINT | quantity | Countable measure. | 1.00 |
| `price_basis` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `quote_unit` | VARCHAR | unit_of_measure | Physical unit a quantity or price is expressed per (troy_oz, lb, metric_ton, ...). Codes are the group units_of_measure seed. | 1.00 |
| `segment` | VARCHAR |  | — | 0.00 |
| `unit_dimension` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [Commodity](/concepts/Commodity.md).

# Lineage

* **Upstream:** `stg_sisters__landed_prices`
* **Downstream:** [rpt_market_comparison_board](/tables/rpt_market_comparison_board.md)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
