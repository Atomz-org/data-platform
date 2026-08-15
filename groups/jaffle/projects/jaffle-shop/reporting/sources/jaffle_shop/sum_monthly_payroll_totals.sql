-- source extract for sum_monthly_payroll_totals (PII columns excluded by the MDL projection)
select pay_period_start, employee_count, total_gross_pay, total_net_pay, total_deductions, avg_gross_per_employee, prior_period_gross
from main_marts.sum_monthly_payroll_totals
