---
type: Table
title: exec_company_kpis_monthly
description: Monthly company KPIs with MoM and YoY growth rates.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:exec_company_kpis_monthly
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `active_days` | BIGINT |  | — | 0.00 |
| `avg_daily_active_customers` | DOUBLE |  | — | 0.00 |
| `avg_ticket_size` | DOUBLE |  | — | 0.00 |
| `mom_orders_growth` | DOUBLE |  | — | 0.00 |
| `mom_revenue_growth` | DOUBLE |  | — | 0.00 |
| `month_start` | TIMESTAMP |  | — | 0.00 |
| `monthly_gross_revenue` | DECIMAL |  | — | 0.00 |
| `monthly_new_customers` | VARCHAR |  | — | 0.00 |
| `monthly_orders` | VARCHAR |  | — | 0.00 |
| `monthly_revenue` | DECIMAL |  | — | 0.00 |
| `monthly_tax` | DECIMAL |  | — | 0.00 |
| `monthly_waste_cost` | DECIMAL |  | — | 0.00 |
| `prev_month_revenue` | DECIMAL |  | — | 0.00 |
| `same_month_last_year_revenue` | DECIMAL |  | — | 0.00 |
| `yoy_revenue_growth` | DOUBLE |  | — | 0.00 |

# Lineage

* **Upstream:** `exec_company_kpis_daily`
* **Read by:** `weekly_business_review` (Finance Team)
