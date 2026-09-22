---
type: Table
title: scr_customer_churn_propensity
description: 0-100 churn risk score per customer based on recency, frequency, loyalty
  activity, and spend trend from dim_customer_360.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:scr_customer_churn_propensity
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `churn_propensity_score` | DOUBLE |  | — | 0.00 |
| `churn_risk_tier` | VARCHAR |  | — | 0.00 |
| `customer_id` | VARCHAR |  | (primary key) | 0.00 |
| `customer_name` | VARCHAR |  | — | 0.00 |
| `days_since_last_order` | BIGINT |  | — | 0.00 |
| `frequency_score` | INTEGER |  | — | 0.00 |
| `lifetime_spend` | DECIMAL |  | — | 0.00 |
| `loyalty_score` | INTEGER |  | — | 0.00 |
| `loyalty_tier` | VARCHAR |  | — | 0.00 |
| `recency_score` | DOUBLE |  | — | 0.00 |
| `rfm_total_score` | BIGINT |  | — | 0.00 |
| `spend_score` | INTEGER |  | — | 0.00 |
| `total_orders` | BIGINT |  | — | 0.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Lineage

* **Upstream:** [dim_customer_360](/tables/dim_customer_360.md)
* **Downstream:** `exec_customer_health_index`, `mega_wide_customer_master`, [rev_etl_email_segment_at_risk](/tables/rev_etl_email_segment_at_risk.md), `rpt_360_customer_health_dashboard`, `rpt_risk_register`, `wide_customer_summary`
* **Read by:** `ml_churn_prediction` (Data Science Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
* **Decision** ADR-0003 — ADR-0003 — What the base/current diff found (accepted · **Stage:** `review` · **Date:**)
