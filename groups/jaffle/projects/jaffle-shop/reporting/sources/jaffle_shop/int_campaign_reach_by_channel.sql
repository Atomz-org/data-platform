-- source extract for int_campaign_reach_by_channel (PII columns excluded by the MDL projection)
select campaign_id, spend_channel, channel_spend, estimated_impressions, channel_spend_share, campaign_name, active_days, first_spend_date, last_spend_date, campaign_total_spend, avg_daily_spend
from main_marts.int_campaign_reach_by_channel
