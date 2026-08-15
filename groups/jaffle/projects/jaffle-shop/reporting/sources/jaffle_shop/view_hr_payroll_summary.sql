-- source extract for view_hr_payroll_summary (PII columns excluded by the MDL projection)
select payroll_month, department_name, total_gross_pay, total_net_pay, employees_paid, avg_gross_per_employee
from main_marts.view_hr_payroll_summary
