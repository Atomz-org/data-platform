---
type: Table
title: rpt_stock_alerts
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: Product
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_stock_alerts
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `current_quantity` | VARCHAR |  | — | 0.00 |
| `daily_depletion_rate` | DOUBLE |  | — | 0.00 |
| `estimated_days_of_stock` | DOUBLE |  | — | 0.00 |
| `last_movement_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `needs_reorder` | BOOLEAN |  | — | 0.00 |
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `reorder_point` | DOUBLE |  | — | 0.00 |
| `stock_alert_level` | VARCHAR |  | — | 0.00 |
| `suggested_reorder_quantity` | DOUBLE |  | — | 0.00 |
| `supplier_avg_lead_time_days` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Product](/concepts/Product.md).

# Lineage

* **Upstream:** `int_inventory_current_level`, `int_reorder_point_calc`
* **Downstream:** [rev_etl_inventory_reorder](/tables/rev_etl_inventory_reorder.md), `rpt_reorder_recommendation`, [view_store_mgr_inventory_status](/tables/view_store_mgr_inventory_status.md), `wide_inventory_summary`
* **Read by:** `inventory_reorder_system` (Supply Chain Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
