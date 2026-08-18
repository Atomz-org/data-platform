-- source extract for dim_customers (PII columns excluded by the MDL projection)
select customer_id, customer_segment, country_code, created_at, subscription_count, active_subscriptions
from main_marts.dim_customers
