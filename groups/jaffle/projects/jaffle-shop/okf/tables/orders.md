---
type: Table
title: orders
description: Order overview data mart, offering key details for each order inlcluding
  if it's a customer's first order and a food vs. drink item breakdown. One row per
  order.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Order
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:orders
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `count_drink_items` | VARCHAR |  | — | 0.00 |
| `count_food_items` | VARCHAR |  | — | 0.00 |
| `count_order_items` | BIGINT |  | — | 0.00 |
| `customer_id` | VARCHAR |  | — | 0.00 |
| `customer_order_number` | BIGINT |  | — | 0.00 |
| `is_drink_order` | BOOLEAN |  | — | 0.00 |
| `is_food_order` | BOOLEAN |  | — | 0.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `order_cost` | DECIMAL |  | — | 0.00 |
| `order_id` | VARCHAR |  | (primary key) | 0.00 |
| `order_items_subtotal` | DECIMAL |  | — | 0.00 |
| `order_total` | DECIMAL |  | — | 0.00 |
| `order_total_cents` | INTEGER |  | — | 0.00 |
| `ordered_at` | TIMESTAMP |  | — | 0.00 |
| `subtotal` | DECIMAL |  | — | 0.00 |
| `subtotal_cents` | INTEGER |  | — | 0.00 |
| `tax_paid` | DECIMAL |  | — | 0.00 |
| `tax_paid_cents` | INTEGER |  | — | 0.00 |

# Concept

Instantiates [Order](/concepts/Order.md).

# Metrics

* [drink_orders](/metrics/drink_orders.md)
* [food_orders](/metrics/food_orders.md)
* [large_orders](/metrics/large_orders.md)
* [new_customer_orders](/metrics/new_customer_orders.md)
* [order_cost](/metrics/order_cost.md)
* [order_total](/metrics/order_total.md)
* [orders](/metrics/orders.md)

# Lineage

* **Upstream:** [order_items](/tables/order_items.md), `stg_orders`
* **Downstream:** `adv_above_store_average`, `adv_conditional_aggregates`, `adv_customer_analysis_cube`, `adv_customer_order_pairs`, `adv_latest_event_per_customer`, `adv_multi_filter_summary`, `cmp_new_vs_returning_customers`, `coh_customer_monthly_cohort`, [customers](/tables/customers.md), `fnl_new_customer_onboarding`, `int_customer_preferred_store`, `mega_wide_customer_master`, [ml_feature_customer_churn](/tables/ml_feature_customer_churn.md), `rpt_churn_risk_dashboard`, `rpt_customer_cohort_retention`, `wide_customer_summary`, `wide_order_detail`, `wide_order_with_customer`, `wide_product_summary`, `wide_store_monthly`
* **Read by:** `report_index` (Data Platform), `report_metrics_drink_orders` (Data Platform), `report_metrics_food_orders` (Data Platform), `report_metrics_large_orders` (Data Platform), `report_metrics_new_customer_orders` (Data Platform), `report_metrics_order_cost` (Data Platform), and 2 more

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
