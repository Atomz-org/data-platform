-- source extract for int_store_marketing_spend (PII columns excluded by the MDL projection)
select store_id, spend_month, monthly_marketing_spend, top_spend_channel, store_name, active_channels, active_spend_days, avg_daily_marketing_spend, top_channel_spend
from main_marts.int_store_marketing_spend
