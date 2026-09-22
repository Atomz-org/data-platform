---
type: Table
title: met_weekly_revenue_by_store
description: Weekly revenue aggregation per store with week-over-week growth.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Location
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:met_weekly_revenue_by_store
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `avg_order_value` | DOUBLE |  | — | 0.00 |
| `location_id` | VARCHAR |  | (primary key) | 0.00 |
| `prev_week_revenue` | DECIMAL |  | — | 0.00 |
| `store_name` | VARCHAR |  | — | 0.00 |
| `week_start` | TIMESTAMP |  | — | 0.00 |
| `weekly_gross_revenue` | DECIMAL |  | — | 0.00 |
| `weekly_orders` | VARCHAR |  | — | 0.00 |
| `weekly_revenue` | DECIMAL |  | — | 0.00 |
| `weekly_tax_collected` | DECIMAL |  | — | 0.00 |
| `wow_revenue_growth` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Location](/concepts/Location.md).

# Lineage

* **Upstream:** `met_daily_revenue_by_store`
* **Downstream:** `alert_revenue_drop_weekly`, `poc_orders_wow`, `poc_revenue_wow`, `trend_aov_weekly`
* **Read by:** `weekly_business_review` (Finance Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
