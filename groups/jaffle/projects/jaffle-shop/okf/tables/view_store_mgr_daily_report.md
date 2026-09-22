---
type: Table
title: view_store_mgr_daily_report
description: Daily store report with revenue, orders, labor cost, waste, and day assessment
  for store managers.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: Location
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:view_store_mgr_daily_report
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `avg_order_value` | DOUBLE |  | — | 0.00 |
| `daily_revenue` | DECIMAL |  | — | 0.00 |
| `day_assessment` | VARCHAR |  | — | 0.00 |
| `labor_cost` | DOUBLE |  | — | 0.00 |
| `labor_cost_pct` | DOUBLE |  | — | 0.00 |
| `labor_hours` | DOUBLE |  | — | 0.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `order_count` | BIGINT |  | — | 0.00 |
| `order_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `waste_cost` | DECIMAL |  | — | 0.00 |
| `waste_pct` | DOUBLE |  | — | 0.00 |

# Concept

Instantiates [Location](/concepts/Location.md).

# Lineage

* **Upstream:** `int_store_daily_summary`
* **Read by:** `store_manager_portal` (Operations Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
