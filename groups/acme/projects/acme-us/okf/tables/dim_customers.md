---
type: Table
title: dim_customers
description: Customer dimension with subscription rollups.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Payment
okf_x_layer: marts
okf_x_grain: one customer
okf_x_columns_withheld: 0
okf_x_kg_node: model:dim_customers
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `active_subscriptions` | BIGINT | quantity | Countable measure. | 1.00 |
| `country_code` | VARCHAR | geo_country | ISO 3166 country code. | 1.00 |
| `created_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `customer_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `customer_segment` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `first_subscribed_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `is_active` | BOOLEAN |  | — | 0.00 |
| `organization_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `subscription_count` | BIGINT | quantity | Countable measure. | 1.00 |

# Concept

Instantiates [Payment](/concepts/Payment.md).

# Metrics

* [active_customers](/metrics/active_customers.md)

# Lineage

* **Upstream:** `stg_stripe__customers`, `stg_stripe__subscriptions`
* **Read by:** `crm_customer_sync` (RevOps), `exec_weekly_dashboard` (Finance), `report_metrics_active_customers` (Data Platform)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
