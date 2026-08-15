-- source extract for int_customer_ltv (PII columns excluded by the MDL projection)
select customer_id, lifetime_spend, total_orders, avg_order_value, customer_tenure_days, ltv_tier, distinct_products_purchased, first_order_at, last_order_at
from main_marts.int_customer_ltv
