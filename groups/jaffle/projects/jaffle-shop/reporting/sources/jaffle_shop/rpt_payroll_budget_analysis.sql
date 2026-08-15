-- source extract for rpt_payroll_budget_analysis (PII columns excluded by the MDL projection)
select department_id, department_name, pay_month, employee_count, total_gross_pay, total_net_pay, total_deductions, total_hours, total_overtime_hours, avg_cost_per_hour, avg_gross_pay_per_employee, prev_month_gross_pay, month_over_month_change_pct, rolling_3mo_avg_gross_pay, overtime_pct_of_total
from main_marts.rpt_payroll_budget_analysis
