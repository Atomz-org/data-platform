-- source extract for fct_revenue (PII columns excluded by the MDL projection)
select revenue_date, net_amount, customer_segment, plan_tier, currency_code, gross_amount, payment_count
from base_marts.fct_revenue
