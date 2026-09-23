---
type: Table
title: view_store_mgr_product_performance
description: Product sales at store level with monthly aggregation and in-store product
  ranking.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:view_store_mgr_product_performance
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `product_rank_in_store` | BIGINT |  | — | 0.00 |
| `sales_month` | TIMESTAMP |  | — | 0.00 |
| `store_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `total_quantity` | VARCHAR |  | — | 0.00 |
| `total_sales` | DECIMAL |  | — | 0.00 |

# Lineage

* **Upstream:** `int_product_sales_by_location`
* **Read by:** `store_manager_portal` (Operations Team)
