-- source extract for rpt_campaign_calendar (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, campaign_status, campaign_start_date, campaign_end_date, campaign_duration_days, is_currently_active, total_spend, attributed_revenue, roi_ratio, effectiveness_tier, concurrent_campaign_count, campaign_phase
from main_marts.rpt_campaign_calendar
