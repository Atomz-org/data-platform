-- source extract for poc_customers_mom (PII columns excluded by the MDL projection)
select month_start, current_customers, prior_month_customers, current_new, prior_month_new, customer_mom_change, customer_mom_change_pct, new_customer_mom_change_pct
from main_marts.poc_customers_mom
