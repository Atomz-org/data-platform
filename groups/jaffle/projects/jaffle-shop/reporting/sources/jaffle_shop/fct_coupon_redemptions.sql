-- source extract for fct_coupon_redemptions (PII columns excluded by the MDL projection)
select redemption_id, coupon_id, order_id, customer_id, discount_applied, redeemed_at, coupon_code, discount_type, campaign_id, order_total, subtotal, ordered_at, discount_pct_of_order, net_order_total
from main_marts.fct_coupon_redemptions
