-- source extract for int_payroll_by_pay_period (PII columns excluded by the MDL projection)
select pay_period_start, pay_period_end, total_gross_pay, deduction_rate_pct, overtime_pct, pay_date, employee_count, total_hours, total_overtime_hours, total_deductions, total_net_pay, avg_gross_pay_per_employee, avg_deductions_per_employee
from main_marts.int_payroll_by_pay_period
