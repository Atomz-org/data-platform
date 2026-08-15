-- source extract for int_coupon_usage_by_customer_segment (PII columns excluded by the MDL projection)
select customer_segment, total_redemptions, unique_customers, redemptions_per_customer, total_discount_given, total_order_revenue, total_net_revenue, avg_discount_per_redemption, avg_order_value
from main_marts.int_coupon_usage_by_customer_segment
