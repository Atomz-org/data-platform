-- source extract for int_coupon_performance (PII columns excluded by the MDL projection)
select coupon_id, total_redemptions, redemption_rate, total_discount_given, coupon_code, discount_type, discount_amount, discount_percent, coupon_status, max_redemptions, valid_from, valid_until, campaign_id, unique_customers, avg_discount_per_redemption, first_redeemed_at, last_redeemed_at
from main_marts.int_coupon_performance
