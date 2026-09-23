---
type: Table
title: fct_revenue
description: Daily revenue by segment and plan. Union-compatible across sisters.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: one day x segment x plan
okf_x_columns_withheld: 0
okf_x_kg_node: model:fct_revenue
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `currency_code` | VARCHAR | currency_code | ISO 4217 code qualifying a money_amount. | 1.00 |
| `customer_segment` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `gross_amount` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `net_amount` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `payment_count` | BIGINT | quantity | Countable measure. | 1.00 |
| `plan_tier` | VARCHAR | status_enum | Lifecycle state. Monitored for category drift. | 1.00 |
| `revenue_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |

# Lineage

* **Upstream:** [fct_payments](/tables/fct_payments.md)
* **Read by:** `exec_weekly_dashboard` (Finance)
