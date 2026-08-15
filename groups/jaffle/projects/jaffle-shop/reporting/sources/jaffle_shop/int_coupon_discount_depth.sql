-- source extract for int_coupon_discount_depth (PII columns excluded by the MDL projection)
select discount_type, avg_effective_discount_pct, total_redemptions, avg_discount_amount, min_effective_discount_pct, max_effective_discount_pct, avg_order_value_with_coupon
from main_marts.int_coupon_discount_depth
