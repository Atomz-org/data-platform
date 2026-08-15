-- source extract for geo_local_marketing_effectiveness (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, total_spend, attributed_revenue, roi_ratio, roi_pct, effectiveness_tier
from main_marts.geo_local_marketing_effectiveness
