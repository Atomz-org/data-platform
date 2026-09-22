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
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `active_subscriptions` | VARCHAR |  | — | 0.00 |
| `country_code` | VARCHAR |  | — | 0.00 |
| `created_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `customer_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `customer_segment` | VARCHAR |  | — | 0.00 |
| `first_subscribed_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `is_active` | BOOLEAN |  | — | 0.00 |
| `organization_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `subscription_count` | BIGINT |  | — | 0.00 |

# Concept

Instantiates [Payment](/concepts/Payment.md).

# Metrics

* [active_customers](/metrics/active_customers.md)
