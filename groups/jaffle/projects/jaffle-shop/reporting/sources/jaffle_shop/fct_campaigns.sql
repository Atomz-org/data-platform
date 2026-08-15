-- source extract for fct_campaigns (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, campaign_status, campaign_description, budget, campaign_start_date, campaign_end_date, created_at, total_spend, channel_count, active_spend_days, first_spend_date, last_spend_date, budget_utilization
from main_marts.fct_campaigns
