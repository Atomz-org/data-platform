-- source extract for poc_employee_headcount_mom (PII columns excluded by the MDL projection)
select month_start, current_headcount, prior_month_headcount, current_new_hires, prior_month_new_hires, headcount_change, headcount_mom_pct
from main_marts.poc_employee_headcount_mom
