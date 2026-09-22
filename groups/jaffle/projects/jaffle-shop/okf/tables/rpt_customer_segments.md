---
type: Table
title: rpt_customer_segments
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_customer_segments
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `avg_days_since_last_order` | DECIMAL |  | — | 0.00 |
| `avg_orders` | DECIMAL |  | — | 0.00 |
| `avg_rfm_score` | DECIMAL |  | — | 0.00 |
| `avg_spend` | DECIMAL |  | — | 0.00 |
| `customer_count` | BIGINT |  | — | 0.00 |
| `customer_segment` | VARCHAR |  | — | 0.00 |
| `segment_pct` | VARCHAR |  | — | 0.00 |
| `segment_revenue_share_pct` | VARCHAR |  | — | 0.00 |
| `total_segment_revenue` | DECIMAL |  | — | 0.00 |

# Lineage

* **Upstream:** `int_customer_rfm_scores`
* **Read by:** `weekly_business_review` (Finance Team)
