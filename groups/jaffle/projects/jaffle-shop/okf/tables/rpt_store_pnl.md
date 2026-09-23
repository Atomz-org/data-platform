---
type: Table
title: rpt_store_pnl
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: Location
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:rpt_store_pnl
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `inventory_holding_cost` | DECIMAL |  | — | 0.00 |
| `labor_cost_ratio_pct` | VARCHAR |  | — | 0.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `marketing_ratio_pct` | VARCHAR |  | — | 0.00 |
| `marketing_spend` | VARCHAR |  | — | 0.00 |
| `monthly_labor_cost` | DOUBLE |  | — | 0.00 |
| `monthly_revenue` | DECIMAL |  | — | 0.00 |
| `net_profit` | DOUBLE |  | — | 0.00 |
| `net_profit_margin_pct` | DOUBLE |  | — | 0.00 |
| `operating_expenses` | DECIMAL |  | — | 0.00 |
| `opex_ratio_pct` | VARCHAR |  | — | 0.00 |
| `report_month` | TIMESTAMP |  | — | 0.00 |
| `store_name` | VARCHAR |  | — | 0.00 |
| `total_costs` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Location](/concepts/Location.md).

# Lineage

* **Upstream:** `int_store_inventory_cost`, `int_store_marketing_spend`, `int_store_revenue_costs`, `stg_locations`
* **Downstream:** `cmp_store_vs_fleet_avg`, `exec_regional_summary`, `fin_breakeven_timeline`, `fin_store_roi`, `geo_store_cluster_analysis`, `geo_store_risk_assessment`, `mega_wide_store_master`, `rpt_360_store_health_dashboard`, `rpt_break_even_by_store`, `rpt_food_cost_variance_alert`, `rpt_store_performance_quadrant`, `scr_store_health`, `view_cfo_profitability_matrix`, `wide_store_monthly`
* **Read by:** `weekly_business_review` (Finance Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
