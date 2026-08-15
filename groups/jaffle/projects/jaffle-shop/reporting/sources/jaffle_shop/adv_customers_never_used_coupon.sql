-- source extract for adv_customers_never_used_coupon (PII columns excluded by the MDL projection)
select customer_id, customer_name, count_lifetime_orders, first_ordered_at, last_ordered_at, lifetime_spend, coupon_opportunity_segment
from main_marts.adv_customers_never_used_coupon
