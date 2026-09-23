---
type: Table
title: view_store_mgr_staff_schedule
description: Staff shift schedule with employee details, hours, and shift status for
  store manager review.
okf_x_source_of_truth: true
okf_x_table_confidence: 1.0
okf_x_concept: null
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:view_store_mgr_staff_schedule
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `actual_hours` | BIGINT |  | — | 0.00 |
| `employee_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `full_name` | VARCHAR |  | — | 0.00 |
| `location_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `position_title` | VARCHAR |  | — | 0.00 |
| `scheduled_end` | TIMESTAMP |  | — | 0.00 |
| `scheduled_hours` | BIGINT |  | — | 0.00 |
| `scheduled_start` | TIMESTAMP |  | — | 0.00 |
| `shift_date` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `shift_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `shift_status` | VARCHAR |  | — | 0.00 |

# Lineage

* **Upstream:** `dim_employees`, `fct_shifts`
* **Read by:** `store_manager_portal` (Operations Team)
