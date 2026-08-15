-- source extract for sum_monthly_campaign_totals (PII columns excluded by the MDL projection)
select month_start, total_marketing_spend, total_campaign_days, overall_roi, prior_month_spend
from main_marts.sum_monthly_campaign_totals
