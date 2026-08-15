-- source extract for mkt_campaign_incrementality (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, campaign_period_revenue, pre_campaign_revenue, incremental_revenue, total_spend, incremental_roi, incrementality_verdict
from main_marts.mkt_campaign_incrementality
