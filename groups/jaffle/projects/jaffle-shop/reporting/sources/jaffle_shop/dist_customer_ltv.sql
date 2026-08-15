-- source extract for dist_customer_ltv (PII columns excluded by the MDL projection)
select ltv_tier, customer_count, avg_lifetime_spend, min_lifetime_spend, max_lifetime_spend, avg_orders
from main_marts.dist_customer_ltv
