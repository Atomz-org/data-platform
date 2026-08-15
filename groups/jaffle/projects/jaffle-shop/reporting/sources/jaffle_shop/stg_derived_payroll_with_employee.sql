-- source extract for stg_derived_payroll_with_employee (PII columns excluded by the MDL projection)
select payroll_id, employee_id, full_name, department_id, location_id, pay_period_start, pay_period_end, pay_date, gross_pay, net_pay, total_deductions
from main_marts.stg_derived_payroll_with_employee
