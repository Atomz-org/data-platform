-- source extract for met_daily_marketing_spend (PII columns excluded by the MDL projection)
select spend_date, spend_channel, total_spend_7d_avg, channel_spend, campaigns_active, total_daily_spend, total_campaigns_active, channels_active, channel_daily_share, channel_spend_7d_avg
from main_marts.met_daily_marketing_spend
