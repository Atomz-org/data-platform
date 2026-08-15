-- source extract for dim_campaigns (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, campaign_status, campaign_description, budget, campaign_start_date, campaign_end_date, created_at, is_currently_active, campaign_duration_days
from main_marts.dim_campaigns
