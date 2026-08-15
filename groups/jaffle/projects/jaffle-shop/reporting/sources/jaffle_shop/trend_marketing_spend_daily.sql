-- source extract for trend_marketing_spend_daily (PII columns excluded by the MDL projection)
select spend_date, spend_channel, total_spend, spend_7d_ma, spend_28d_ma, spend_28d_total, spend_same_day_last_week
from main_marts.trend_marketing_spend_daily
