-- source extract for fnl_campaign_to_purchase (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaign_id,
    campaign_name,
    stage_1_coupon_recipients,
    stage_2_redeemed,
    stage_3_repeat_purchase,
    redemption_rate_pct,
    repeat_purchase_rate_pct
from main_marts.fnl_campaign_to_purchase
