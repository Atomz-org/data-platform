---
type: Table
title: rev_etl_email_segment_at_risk
description: At-risk customers for win-back email campaigns filtered by churn propensity
  score above 70.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rev_etl_email_segment_at_risk
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `churn_propensity_score` | DOUBLE |  | — | 0.00 |
| `customer_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `customer_name` | VARCHAR |  | — | 0.00 |
| `email_segment` | VARCHAR |  | — | 0.00 |
| `exported_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `last_order_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `lifetime_spend` | DECIMAL |  | — | 0.00 |
| `total_orders` | BIGINT |  | — | 0.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Lineage

* **Upstream:** [dim_customer_360](/tables/dim_customer_360.md), [scr_customer_churn_propensity](/tables/scr_customer_churn_propensity.md)
* **Read by:** `crm_sync` (Marketing Ops)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
