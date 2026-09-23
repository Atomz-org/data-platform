---
type: Table
title: ml_feature_customer_churn
description: 'Customer-level feature table for churn prediction models. Includes recency,
  frequency, monetary, loyalty, engagement, and trend features plus a proxy churn
  label (no order in 90+ days). Grain: one row per customer.'
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:ml_feature_customer_churn
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `avg_order_value` | DOUBLE |  | — | 0.00 |
| `churn_label_proxy` | INTEGER |  | — | 0.00 |
| `coupons_redeemed` | BIGINT |  | — | 0.00 |
| `customer_id` | VARCHAR |  | (primary key) | 0.00 |
| `customer_tenure_days` | BIGINT |  | — | 0.00 |
| `days_since_last_order` | BIGINT |  | — | 0.00 |
| `distinct_stores_visited` | BIGINT |  | — | 0.00 |
| `frequency_score` | BIGINT |  | — | 0.00 |
| `is_loyalty_member` | INTEGER |  | — | 0.00 |
| `lifetime_order_count` | BIGINT |  | — | 0.00 |
| `lifetime_spend` | DECIMAL |  | — | 0.00 |
| `loyalty_points_balance` | VARCHAR |  | — | 0.00 |
| `loyalty_tier` | VARCHAR |  | — | 0.00 |
| `marketing_engagement_level` | VARCHAR |  | — | 0.00 |
| `monetary_score` | BIGINT |  | — | 0.00 |
| `order_trend_slope` | DOUBLE |  | — | 0.00 |
| `orders_per_month` | DOUBLE |  | — | 0.00 |
| `prior_3m_order_avg` | DOUBLE |  | — | 0.00 |
| `recency_score` | BIGINT |  | — | 0.00 |
| `recent_3m_order_avg` | DOUBLE |  | — | 0.00 |
| `rfm_segment_code` | VARCHAR |  | — | 0.00 |
| `rfm_total_score` | BIGINT |  | — | 0.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Lineage

* **Upstream:** [dim_customer_360](/tables/dim_customer_360.md), `int_customer_rfm_scores`, [orders](/tables/orders.md)
* **Read by:** `ml_churn_prediction` (Data Science Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
* **Decision** ADR-0003 — ADR-0003 — What the base/current diff found (accepted · **Stage:** `review` · **Date:**)
