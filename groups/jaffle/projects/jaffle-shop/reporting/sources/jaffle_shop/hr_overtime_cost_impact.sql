-- source extract for hr_overtime_cost_impact (PII columns excluded by the MDL projection)
select employee_id, month_start, overtime_hours, regular_hours, total_hours, avg_hourly_rate, estimated_overtime_cost, monthly_gross_pay, overtime_cost_pct_of_pay
from main_marts.hr_overtime_cost_impact
