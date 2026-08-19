-- source extract for int_campaign_reach_by_channel (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaign_id,
    spend_channel,
    channel_spend,
    estimated_impressions,
    channel_spend_share
from main_marts.int_campaign_reach_by_channel
