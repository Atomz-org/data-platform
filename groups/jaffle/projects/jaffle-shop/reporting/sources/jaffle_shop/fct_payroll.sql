-- source extract for fct_payroll (PII columns excluded by the MDL projection)
select payroll_id, employee_id, full_name, department_name, position_title, location_id, pay_period_start, pay_period_end, pay_date, payroll_hours, payroll_overtime_hours, gross_pay, deductions, net_pay, effective_hourly_rate, deduction_pct
from main_marts.fct_payroll
