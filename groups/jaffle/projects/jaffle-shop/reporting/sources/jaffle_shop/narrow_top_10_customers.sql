-- source extract for narrow_top_10_customers (PII columns excluded by the MDL projection)
select customer_id, customer_name, lifetime_spend
from main_marts.narrow_top_10_customers
