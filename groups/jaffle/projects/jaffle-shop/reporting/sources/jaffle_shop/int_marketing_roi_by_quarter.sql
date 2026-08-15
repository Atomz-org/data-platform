-- source extract for int_marketing_roi_by_quarter (PII columns excluded by the MDL projection)
select roi_quarter, quarterly_roi_pct, revenue_per_marketing_dollar, campaigns_count, campaign_direct_cost, total_marketing_spend, total_attributed_revenue, avg_campaign_roi_pct
from main_marts.int_marketing_roi_by_quarter
