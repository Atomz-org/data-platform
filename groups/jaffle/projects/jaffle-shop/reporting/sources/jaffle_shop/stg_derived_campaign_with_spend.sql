-- source extract for stg_derived_campaign_with_spend (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, campaign_start_date, campaign_end_date, campaign_status, total_spend
from main_marts.stg_derived_campaign_with_spend
