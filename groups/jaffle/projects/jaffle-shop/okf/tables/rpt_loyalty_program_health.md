---
type: Table
title: rpt_loyalty_program_health
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_loyalty_program_health
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `active_members` | BIGINT |  | — | 0.00 |
| `avg_current_balance` | DOUBLE |  | — | 0.00 |
| `avg_lifetime_points` | DOUBLE |  | — | 0.00 |
| `avg_points_earned` | DOUBLE |  | — | 0.00 |
| `avg_points_redeemed` | DOUBLE |  | — | 0.00 |
| `current_tier_name` | VARCHAR |  | — | 0.00 |
| `member_count` | BIGINT |  | — | 0.00 |
| `program_active_members` | VARCHAR |  | — | 0.00 |
| `program_redemption_rate` | DOUBLE |  | — | 0.00 |
| `program_total_members` | BIGINT |  | — | 0.00 |
| `tier_member_share` | DOUBLE |  | — | 0.00 |
| `tier_redemption_rate` | DOUBLE |  | — | 0.00 |

# Lineage

* **Upstream:** `fct_loyalty_transactions`, `int_loyalty_tier_progression`
* **Downstream:** `view_cmo_loyalty_overview`
* **Read by:** `marketing_analytics` (Marketing Team)
