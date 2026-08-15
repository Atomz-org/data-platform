-- source extract for sum_monthly_department_totals (PII columns excluded by the MDL projection)
select payroll_month, department_id, employee_count, total_gross_pay, total_net_pay, avg_pay_per_employee
from main_marts.sum_monthly_department_totals
