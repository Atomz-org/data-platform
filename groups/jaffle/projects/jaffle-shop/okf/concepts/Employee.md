---
type: Concept
title: Employee
description: Internal actor. Rarely modelled in marts; used for attribution.
okf_x_defined_in: platform
okf_x_parent: Party
okf_x_identity: employee_id
okf_x_kg_node: concept:Employee
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Employee.md
---

Defined by the platform ontology: [Employee](../../../../../../platform/okf/concepts/Employee.md).

# Instantiated by

* [adv_org_hierarchy](/tables/adv_org_hierarchy.md)
* [alert_employee_no_show_pattern](/tables/alert_employee_no_show_pattern.md)
* [alert_overtime_excessive](/tables/alert_overtime_excessive.md)
* [alert_training_overdue](/tables/alert_training_overdue.md)
* [dim_employees](/tables/dim_employees.md)
* [dq_shift_overlap_check](/tables/dq_shift_overlap_check.md)
* [hr_attrition_risk_factors](/tables/hr_attrition_risk_factors.md)
* [hr_compensation_analysis](/tables/hr_compensation_analysis.md)
* [hr_cross_training_coverage](/tables/hr_cross_training_coverage.md)
* [hr_employee_cost_per_order](/tables/hr_employee_cost_per_order.md)
* [hr_employee_engagement_proxy](/tables/hr_employee_engagement_proxy.md)
* [hr_employee_journey](/tables/hr_employee_journey.md)
* [hr_onboarding_time_to_value](/tables/hr_onboarding_time_to_value.md)
* [hr_overtime_cost_impact](/tables/hr_overtime_cost_impact.md)
* [hr_payroll_variance](/tables/hr_payroll_variance.md)
* [hr_shift_preference_fulfillment](/tables/hr_shift_preference_fulfillment.md)
* [hr_succession_planning](/tables/hr_succession_planning.md)
* [hr_training_gap_analysis](/tables/hr_training_gap_analysis.md)
* [int_absenteeism_rate](/tables/int_absenteeism_rate.md)
* [int_employee_availability](/tables/int_employee_availability.md)
* [int_employee_cross_location](/tables/int_employee_cross_location.md)
* [int_employee_enriched](/tables/int_employee_enriched.md)
* [int_employee_monthly_metrics](/tables/int_employee_monthly_metrics.md)
* [int_employee_productivity](/tables/int_employee_productivity.md)
* [int_employee_schedule_adherence](/tables/int_employee_schedule_adherence.md)
* [int_employee_tenure](/tables/int_employee_tenure.md)
* [int_labor_hours_actual](/tables/int_labor_hours_actual.md)
* [int_new_hire_training_progress](/tables/int_new_hire_training_progress.md)
* [int_overtime_hours](/tables/int_overtime_hours.md)
* [int_shift_pattern_by_employee](/tables/int_shift_pattern_by_employee.md)
* [int_training_progress](/tables/int_training_progress.md)
* [ml_feature_employee_attrition](/tables/ml_feature_employee_attrition.md)
* [rank_employees_by_performance](/tables/rank_employees_by_performance.md)
* [rank_employees_by_productivity](/tables/rank_employees_by_productivity.md)
* [rank_employees_by_tenure](/tables/rank_employees_by_tenure.md)
* [rpt_employee_development_tracker](/tables/rpt_employee_development_tracker.md)
* [rpt_employee_productivity_ranking](/tables/rpt_employee_productivity_ranking.md)
* [rpt_employee_satisfaction_proxy](/tables/rpt_employee_satisfaction_proxy.md)
* [rpt_labor_compliance](/tables/rpt_labor_compliance.md)
* [rpt_training_investment_return](/tables/rpt_training_investment_return.md)
* [scr_employee_performance](/tables/scr_employee_performance.md)
* [stg_derived_employee_with_department](/tables/stg_derived_employee_with_department.md)
* [stg_derived_employee_with_position](/tables/stg_derived_employee_with_position.md)
* [view_hr_performance_overview](/tables/view_hr_performance_overview.md)
* [wide_employee_summary](/tables/wide_employee_summary.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `department_id` | integer | foreign_key |
| `employee_id` | string | natural_key |
| `hire_date` | date | event_time |
| `id` | integer | natural_key |
| `position_id` | integer | foreign_key |
| `store_id` | integer | foreign_key |
| `termination_date` | date | event_time |

# Raw tables that instantiate it

* `jaffle-seeds.raw_employees`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
