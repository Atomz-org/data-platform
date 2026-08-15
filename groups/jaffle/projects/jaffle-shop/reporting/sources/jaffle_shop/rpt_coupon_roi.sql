-- source extract for rpt_coupon_roi (PII columns excluded by the MDL projection)
select coupon_id, coupon_code, discount_type, discount_amount, discount_percent, coupon_status, campaign_id, total_redemptions, unique_customers, total_discount_given, avg_discount_per_redemption, redemption_rate, valid_from, valid_until, campaign_name, campaign_channel, campaign_total_spend, campaign_attributed_revenue, campaign_roi_ratio, estimated_coupon_roi
from main_marts.rpt_coupon_roi
