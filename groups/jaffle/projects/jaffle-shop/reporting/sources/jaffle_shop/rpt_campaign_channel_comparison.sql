-- source extract for rpt_campaign_channel_comparison (PII columns excluded by the MDL projection)
select campaign_channel, campaign_count, total_spend, total_revenue, total_orders, total_customers, channel_roi, avg_cost_per_order, total_estimated_impressions, total_active_days, avg_daily_spend, estimated_conversion_rate, revenue_per_impression
from main_marts.rpt_campaign_channel_comparison
