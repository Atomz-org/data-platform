-- source extract for rpt_overtime_analysis (PII columns excluded by the MDL projection)
select location_id, week_start, employees_with_overtime, total_overtime_hours, avg_overtime_hours_per_employee, daily_threshold_overtime, weekly_threshold_overtime, total_regular_hours, total_labor_cost, overtime_pct_of_total_hours
from main_marts.rpt_overtime_analysis
