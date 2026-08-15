-- source extract for inc_fct_coupon_redemptions (PII columns excluded by the MDL projection)
select redemption_id, coupon_id, customer_id, order_id, redeemed_at, discount_applied, redemption_date, redemption_month
from main_marts.inc_fct_coupon_redemptions
