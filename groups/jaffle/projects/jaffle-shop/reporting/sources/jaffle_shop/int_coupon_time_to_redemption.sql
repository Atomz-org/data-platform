-- source extract for int_coupon_time_to_redemption (PII columns excluded by the MDL projection)
select coupon_id, days_to_first_redemption, redemption_speed, coupon_code, discount_type, valid_from, valid_until, first_redemption_date, total_redemptions
from main_marts.int_coupon_time_to_redemption
