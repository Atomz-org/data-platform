---
type: Table
title: products
description: Every product the shop sells, one row per product, straight from the
  source.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Product
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:products
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `is_drink_item` | BOOLEAN |  | — | 0.00 |
| `is_food_item` | BOOLEAN |  | — | 0.00 |
| `product_description` | VARCHAR |  | — | 0.00 |
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `product_name` | VARCHAR |  | — | 0.00 |
| `product_price` | DECIMAL |  | — | 0.00 |
| `product_type` | VARCHAR |  | — | 0.00 |

# Concept

Instantiates [Product](/concepts/Product.md).

# Lineage

* **Upstream:** `stg_products`
* **Downstream:** `rpt_demand_planning_dashboard`, `rpt_menu_availability_risk`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
