-- source extract for view_cmo_campaign_dashboard (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, total_spend, total_revenue_attributed, roi_pct, total_conversions, cost_per_conversion, effectiveness_tier, campaign_tier
from main_marts.view_cmo_campaign_dashboard
