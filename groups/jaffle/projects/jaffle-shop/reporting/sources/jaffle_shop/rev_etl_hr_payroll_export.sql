-- source extract for rev_etl_hr_payroll_export (PII columns excluded by the MDL projection)
select payroll_id, employee_id, department_name, pay_period_start, pay_period_end, payroll_hours, payroll_overtime_hours, gross_pay, deductions, net_pay, exported_at, source_system
from main_marts.rev_etl_hr_payroll_export
