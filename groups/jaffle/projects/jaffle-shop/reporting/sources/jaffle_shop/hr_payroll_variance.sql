-- source extract for hr_payroll_variance (PII columns excluded by the MDL projection)
select employee_id, pay_month, total_gross_pay, expected_pay_from_hours, pay_variance, expected_hours, actual_hours, hours_variance, variance_status
from main_marts.hr_payroll_variance
