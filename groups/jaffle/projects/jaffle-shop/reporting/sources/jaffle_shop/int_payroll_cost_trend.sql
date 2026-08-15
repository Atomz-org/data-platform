-- source extract for int_payroll_cost_trend (PII columns excluded by the MDL projection)
select department_id, department_name, pay_month, employee_count, total_hours, total_overtime_hours, total_gross_pay, total_deductions, total_net_pay, avg_cost_per_hour, avg_gross_pay_per_employee, prev_month_gross_pay, month_over_month_change_pct
from main_marts.int_payroll_cost_trend
