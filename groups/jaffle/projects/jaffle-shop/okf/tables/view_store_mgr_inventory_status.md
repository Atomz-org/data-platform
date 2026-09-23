---
type: Table
title: view_store_mgr_inventory_status
description: Current inventory levels with reorder alerts and urgency classification
  for store managers.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Location
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:view_store_mgr_inventory_status
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `action_needed` | VARCHAR |  | — | 0.00 |
| `current_quantity` | VARCHAR |  | — | 0.00 |
| `estimated_days_of_stock` | DOUBLE |  | — | 0.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `reorder_point` | DOUBLE |  | — | 0.00 |
| `stock_alert_level` | VARCHAR |  | — | 0.00 |
| `urgency` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [Location](/concepts/Location.md).

# Lineage

* **Upstream:** [rpt_stock_alerts](/tables/rpt_stock_alerts.md)
* **Read by:** `store_manager_portal` (Operations Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
