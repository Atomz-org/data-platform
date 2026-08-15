-- source extract for int_payroll_tax_by_jurisdiction (PII columns excluded by the MDL projection)
select location_id, payroll_month, total_gross_pay, effective_deduction_rate_pct, location_name, employee_count, total_deductions, total_net_pay, avg_gross_pay
from main_marts.int_payroll_tax_by_jurisdiction
