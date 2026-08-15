-- source extract for hr_department_budget_utilization (PII columns excluded by the MDL projection)
select department_name, pay_month, total_labor_spend, employee_count, monthly_budget_allocation, budget_variance, budget_utilization_pct, ytd_labor_spend
from main_marts.hr_department_budget_utilization
