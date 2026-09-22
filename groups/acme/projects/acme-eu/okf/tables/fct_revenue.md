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
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `currency_code` | VARCHAR |  | — | 0.00 |
| `customer_segment` | VARCHAR |  | — | 0.00 |
| `gross_amount` | DECIMAL |  | — | 0.00 |
| `net_amount` | DECIMAL | money_amount | Monetary value. Requires a sibling currency_code. | 1.00 |
| `payment_count` | BIGINT |  | — | 0.00 |
| `plan_tier` | VARCHAR |  | — | 0.00 |
| `revenue_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
