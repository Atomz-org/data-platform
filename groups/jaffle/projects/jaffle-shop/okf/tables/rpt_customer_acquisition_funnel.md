---
type: Table
title: rpt_customer_acquisition_funnel
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_customer_acquisition_funnel
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `acquisition_source` | VARCHAR |  | — | 0.00 |
| `customers_from_referral` | BIGINT |  | — | 0.00 |
| `customers_with_campaign` | BIGINT |  | — | 0.00 |
| `source_rank` | BIGINT |  | — | 0.00 |
| `source_share` | DOUBLE |  | — | 0.00 |
| `total_customers` | BIGINT |  | — | 0.00 |

# Lineage

* **Upstream:** `int_customer_acquisition_source`
* **Downstream:** `view_cmo_acquisition_funnel`
* **Read by:** `marketing_analytics` (Marketing Team)
