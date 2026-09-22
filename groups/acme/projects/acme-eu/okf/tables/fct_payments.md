---
type: Table
title: fct_payments
description: Payment fact at attempt grain, enriched with customer and plan.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: one payment attempt
okf_x_columns_withheld: 0
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `amount` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `country_code` | VARCHAR |  | — | 0.00 |
| `currency_code` | VARCHAR |  | — | 0.00 |
| `customer_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_customers](/tables/dim_customers.md) | 1.00 |
| `customer_segment` | VARCHAR |  | — | 0.00 |
| `paid_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `payment_id` | VARCHAR | natural_key | Business key from the source system. (primary key) | 1.00 |
| `payment_status` | VARCHAR |  | — | 0.00 |
| `plan_tier` | VARCHAR |  | — | 0.00 |
| `subscription_id` | VARCHAR | foreign_key | Reference to another concept instance. FK to [dim_customers](/tables/dim_customers.md) | 1.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Metrics

* [aov](/metrics/aov.md)
* [gross_payment_volume](/metrics/gross_payment_volume.md)
* [payment_count](/metrics/payment_count.md)
* [revenue](/metrics/revenue.md)
