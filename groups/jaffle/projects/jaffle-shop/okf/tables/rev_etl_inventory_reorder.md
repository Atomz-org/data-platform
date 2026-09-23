---
type: Table
title: rev_etl_inventory_reorder
description: Items needing reorder for procurement system integration based on stock
  alerts for stockout and low stock conditions.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Location
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rev_etl_inventory_reorder
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `current_quantity` | VARCHAR |  | — | 0.00 |
| `estimated_days_of_stock` | DOUBLE |  | — | 0.00 |
| `exported_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `reorder_point` | DOUBLE |  | — | 0.00 |
| `reorder_trigger` | VARCHAR |  | — | 0.00 |
| `stock_alert_level` | VARCHAR |  | — | 0.00 |
| `suggested_reorder_quantity` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Location](/concepts/Location.md).

# Lineage

* **Upstream:** [rpt_stock_alerts](/tables/rpt_stock_alerts.md)
* **Read by:** `inventory_reorder_system` (Supply Chain Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
