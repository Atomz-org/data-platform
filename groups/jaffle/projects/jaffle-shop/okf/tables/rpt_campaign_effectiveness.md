---
type: Table
title: rpt_campaign_effectiveness
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_campaign_effectiveness
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `attributed_customers` | BIGINT |  | — | 0.00 |
| `attributed_orders` | BIGINT |  | — | 0.00 |
| `attributed_revenue` | DECIMAL |  | — | 0.00 |
| `campaign_channel` | VARCHAR |  | — | 0.00 |
| `campaign_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `campaign_name` | VARCHAR |  | — | 0.00 |
| `cost_per_order` | DOUBLE |  | — | 0.00 |
| `effectiveness_tier` | VARCHAR |  | — | 0.00 |
| `first_spend_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `last_spend_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `net_profit` | DECIMAL |  | — | 0.00 |
| `revenue_per_customer` | DOUBLE |  | — | 0.00 |
| `roi_ratio` | DOUBLE |  | — | 0.00 |
| `total_discounts_given` | DECIMAL |  | — | 0.00 |
| `total_spend` | DECIMAL |  | — | 0.00 |

# Lineage

* **Upstream:** `int_campaign_roi`
* **Downstream:** `rpt_campaign_calendar`, `view_cmo_campaign_dashboard`, `wide_campaign_summary`
* **Read by:** `marketing_analytics` (Marketing Team)
