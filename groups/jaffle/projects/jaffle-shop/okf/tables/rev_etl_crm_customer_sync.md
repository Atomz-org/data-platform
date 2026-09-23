---
type: Table
title: rev_etl_crm_customer_sync
description: Customer data formatted for CRM sync including name, segment, LTV, and
  churn risk with source system metadata.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rev_etl_crm_customer_sync
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `customer_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `customer_name` | VARCHAR |  | — | 0.00 |
| `first_order_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `last_order_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `lifetime_spend` | DECIMAL |  | — | 0.00 |
| `ltv_tier` | VARCHAR |  | — | 0.00 |
| `preferred_store_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `rfm_total_score` | BIGINT |  | — | 0.00 |
| `source_system` | VARCHAR |  | — | 0.00 |
| `synced_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `total_orders` | BIGINT |  | — | 0.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Lineage

* **Upstream:** [dim_customer_360](/tables/dim_customer_360.md)
* **Read by:** `crm_sync` (Marketing Ops)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
* **Decision** ADR-0003 — ADR-0003 — What the base/current diff found (accepted · **Stage:** `review` · **Date:**)
