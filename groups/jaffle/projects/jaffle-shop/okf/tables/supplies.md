---
type: Table
title: supplies
description: Every supply a product consumes, one row per product-supply pair.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:supplies
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `is_perishable_supply` | BOOLEAN |  | — | 0.00 |
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `supply_cost` | DECIMAL |  | — | 0.00 |
| `supply_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `supply_name` | VARCHAR |  | — | 0.00 |
| `supply_uuid` | VARCHAR |  | — | 0.00 |

# Lineage

* **Upstream:** `stg_supplies`
