-- source extract for stg_derived_coupon_with_campaign (PII columns excluded by the MDL projection)
select coupon_id, coupon_code, discount_type, discount_amount, campaign_id, campaign_name, campaign_channel, valid_from, valid_until, coupon_status
from main_marts.stg_derived_coupon_with_campaign
