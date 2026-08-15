-- source extract for poc_payroll_mom (PII columns excluded by the MDL projection)
select pay_period_start, current_gross, prior_month_gross, current_net, prior_month_net, current_employees, prior_month_employees, gross_mom_pct, avg_pay_per_employee
from main_marts.poc_payroll_mom
