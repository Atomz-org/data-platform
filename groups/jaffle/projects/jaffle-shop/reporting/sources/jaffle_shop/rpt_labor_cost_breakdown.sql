-- source extract for rpt_labor_cost_breakdown (PII columns excluded by the MDL projection)
select department_name, pay_grade, work_month, employee_count, total_hours, total_labor_cost, avg_hourly_rate, overtime_hours, regular_hours, overtime_pct
from main_marts.rpt_labor_cost_breakdown
