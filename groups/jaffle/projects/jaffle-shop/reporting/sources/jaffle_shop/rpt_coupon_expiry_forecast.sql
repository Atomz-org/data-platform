-- source extract for rpt_coupon_expiry_forecast (PII columns excluded by the MDL projection)
select coupon_id, coupon_code, campaign_id, discount_type, discount_amount, discount_percent, discount_description, coupon_status, valid_from, valid_until, max_redemptions, is_currently_valid, actual_redemptions, total_discount_used, remaining_redemptions, days_until_expiry, expiry_status, estimated_unused_liability, utilization_rate
from main_marts.rpt_coupon_expiry_forecast
