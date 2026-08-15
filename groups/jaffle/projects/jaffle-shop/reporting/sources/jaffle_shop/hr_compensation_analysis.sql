-- source extract for hr_compensation_analysis (PII columns excluded by the MDL projection)
select employee_id, full_name, position_title, department_name, is_active, avg_monthly_pay, avg_hourly_rate, min_hourly_rate, max_hourly_rate, salary_range_penetration_pct, dept_avg_monthly_pay, pay_vs_dept_avg
from main_marts.hr_compensation_analysis
