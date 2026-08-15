-- source extract for dim_coupons (PII columns excluded by the MDL projection)
select coupon_id, coupon_code, campaign_id, discount_type, discount_amount, discount_percent, minimum_order_amount, max_redemptions, coupon_status, valid_from, valid_until, created_at, discount_description, is_currently_valid
from main_marts.dim_coupons
