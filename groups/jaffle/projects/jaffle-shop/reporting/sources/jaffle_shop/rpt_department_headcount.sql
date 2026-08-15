-- source extract for rpt_department_headcount (PII columns excluded by the MDL projection)
select department_name, total_employees, active_employees, inactive_employees, new_hires, long_tenured, avg_active_tenure_days, avg_active_tenure_months, new_hire_pct, attrition_rate_pct
from main_marts.rpt_department_headcount
