---
type: Table
title: order_items
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:order_items
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `is_drink_item` | BOOLEAN |  | — | 0.00 |
| `is_food_item` | BOOLEAN |  | — | 0.00 |
| `order_id` | VARCHAR |  | — | 0.00 |
| `order_item_id` | VARCHAR |  | (primary key) | 0.00 |
| `ordered_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `product_name` | VARCHAR |  | — | 0.00 |
| `product_price` | DECIMAL |  | — | 0.00 |
| `supply_cost` | DECIMAL |  | — | 0.00 |

# Metrics

* [drink_revenue](/metrics/drink_revenue.md)
* [drink_revenue_pct](/metrics/drink_revenue_pct.md)
* [food_revenue](/metrics/food_revenue.md)
* [food_revenue_pct](/metrics/food_revenue_pct.md)
* [median_revenue](/metrics/median_revenue.md)
* [revenue](/metrics/revenue.md)

# Lineage

* **Upstream:** `stg_order_items`, `stg_orders`, `stg_products`, `stg_supplies`
* **Downstream:** `adv_customer_order_pairs`, `int_customer_ltv`, `int_customer_rfm_scores`, [orders](/tables/orders.md), `wide_order_detail`, `wide_order_with_products`, `wide_product_summary`, `wide_store_monthly`
* **Also measured by:** `cumulative_revenue`
* **Read by:** `report_index` (Data Platform), `report_metrics_drink_revenue` (Data Platform), `report_metrics_drink_revenue_pct` (Data Platform), `report_metrics_food_revenue` (Data Platform), `report_metrics_food_revenue_pct` (Data Platform), `report_metrics_median_revenue` (Data Platform), and 1 more
