-- source extract for rpt_marketing_mix_summary (PII columns excluded by the MDL projection)
select month, spend_channel, monthly_channel_spend, total_monthly_spend, channel_spend_share, channel_total_impressions, channel_total_revenue, channel_total_orders, channel_roi, channel_revenue_per_dollar
from main_marts.rpt_marketing_mix_summary
