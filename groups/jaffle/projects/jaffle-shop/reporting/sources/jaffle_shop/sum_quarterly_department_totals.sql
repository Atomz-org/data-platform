-- source extract for sum_quarterly_department_totals (PII columns excluded by the MDL projection)
select payroll_quarter, department_id, avg_headcount, total_payroll, avg_pay_per_employee_month
from main_marts.sum_quarterly_department_totals
