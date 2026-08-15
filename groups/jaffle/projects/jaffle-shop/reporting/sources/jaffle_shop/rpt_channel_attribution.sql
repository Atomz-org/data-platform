-- source extract for rpt_channel_attribution (PII columns excluded by the MDL projection)
select channel, customers_acquired, total_spend, total_revenue, total_orders, campaign_count, cost_per_acquisition, channel_roi, revenue_per_customer
from main_marts.rpt_channel_attribution
