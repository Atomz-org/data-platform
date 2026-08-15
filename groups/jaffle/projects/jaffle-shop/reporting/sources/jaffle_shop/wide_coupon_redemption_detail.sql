-- source extract for wide_coupon_redemption_detail (PII columns excluded by the MDL projection)
select redemption_id, coupon_id, coupon_code, discount_type, discount_applied, customer_id, customer_name, order_id, redeemed_at, campaign_id, campaign_name
from main_marts.wide_coupon_redemption_detail
