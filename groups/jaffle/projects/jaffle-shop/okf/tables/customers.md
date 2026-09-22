---
type: Table
title: customers
description: Customer overview data mart, offering key details for each unique customer.
  One row per customer.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:customers
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `count_lifetime_orders` | BIGINT |  | — | 0.00 |
| `customer_id` | VARCHAR |  | (primary key) | 0.00 |
| `customer_name` | VARCHAR |  | — | 0.00 |
| `customer_type` | VARCHAR |  | — | 0.00 |
| `first_ordered_at` | TIMESTAMP |  | — | 0.00 |
| `last_ordered_at` | TIMESTAMP |  | — | 0.00 |
| `lifetime_spend` | DECIMAL |  | — | 0.00 |
| `lifetime_spend_pretax` | DECIMAL |  | — | 0.00 |
| `lifetime_tax_paid` | DECIMAL |  | — | 0.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Metrics

* [average_order_value](/metrics/average_order_value.md)
* [count_lifetime_orders](/metrics/count_lifetime_orders.md)
* [lifetime_spend_pretax](/metrics/lifetime_spend_pretax.md)

# Lineage

* **Upstream:** [orders](/tables/orders.md), `stg_customers`
* **Downstream:** `adv_conditional_aggregates`, `adv_customer_analysis_cube`, `adv_customers_never_used_coupon`, `adv_multi_filter_summary`, `cmp_new_vs_returning_customers`, `coh_customer_monthly_cohort`, [dim_customer_360](/tables/dim_customer_360.md), `int_coupon_usage_by_customer_segment`, `int_daily_customer_activity`, `int_new_vs_returning_product_mix`, `mega_wide_customer_master`, `narrow_customer_count_by_type`, `rpt_customer_favorites`, `rpt_customer_reactivation`, `wide_customer_summary`, `wide_order_detail`
* **Read by:** `report_metrics_count_lifetime_orders` (Data Platform), `report_metrics_lifetime_spend_pretax` (Data Platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
