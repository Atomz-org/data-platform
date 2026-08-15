-- source extract for int_marketing_spend_daily (PII columns excluded by the MDL projection)
select spend_date, spend_channel, channel_spend, total_daily_spend, channel_spend_7d_avg, campaigns_active, total_campaigns_active, channels_active, channel_daily_share
from main_marts.int_marketing_spend_daily
