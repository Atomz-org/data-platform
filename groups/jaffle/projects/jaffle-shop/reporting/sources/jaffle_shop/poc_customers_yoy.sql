-- source extract for poc_customers_yoy (PII columns excluded by the MDL projection)
select month_start, current_customers, prior_year_customers, current_new, prior_year_new, customer_yoy_change_pct
from main_marts.poc_customers_yoy
