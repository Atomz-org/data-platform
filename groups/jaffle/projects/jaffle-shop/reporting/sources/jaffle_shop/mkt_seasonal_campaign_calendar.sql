-- source extract for mkt_seasonal_campaign_calendar (PII columns excluded by the MDL projection)
select start_month, campaign_channel, campaigns_run, avg_roi, total_revenue, total_spend, avg_revenue_per_campaign, season_rating
from main_marts.mkt_seasonal_campaign_calendar
