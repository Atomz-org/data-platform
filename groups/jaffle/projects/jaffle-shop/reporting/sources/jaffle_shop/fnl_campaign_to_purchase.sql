-- source extract for fnl_campaign_to_purchase (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, stage_1_coupon_recipients, stage_2_redeemed, stage_3_repeat_purchase, redemption_rate_pct, repeat_purchase_rate_pct, campaign_channel, stage_2_orders
from main_marts.fnl_campaign_to_purchase
