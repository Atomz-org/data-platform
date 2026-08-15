-- source extract for int_coupon_cannibalization (PII columns excluded by the MDL projection)
select coupon_id, cannibalization_rate, incremental_redemptions, cannibalized_redemptions, total_redemptions, cannibalized_discount_cost, incremental_discount_cost, total_order_revenue, total_discount_cost
from main_marts.int_coupon_cannibalization
