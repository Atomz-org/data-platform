-- source extract for kpi_campaign_roi_avg (PII columns excluded by the MDL projection)
select month_start, total_marketing_spend, total_campaign_days, avg_roi, avg_spend_per_campaign
from main_marts.kpi_campaign_roi_avg
