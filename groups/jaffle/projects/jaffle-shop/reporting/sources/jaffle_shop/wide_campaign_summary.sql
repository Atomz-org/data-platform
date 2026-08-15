-- source extract for wide_campaign_summary (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, campaign_start_date, campaign_end_date, budget, total_spend, attributed_revenue, attributed_orders, roi_pct, cost_per_order, roi_attributed_revenue, campaign_performance_tier
from main_marts.wide_campaign_summary
