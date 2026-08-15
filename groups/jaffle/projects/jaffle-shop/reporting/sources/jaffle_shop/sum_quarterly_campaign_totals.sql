-- source extract for sum_quarterly_campaign_totals (PII columns excluded by the MDL projection)
select metric_quarter, quarterly_spend, quarterly_campaigns, quarterly_revenue, quarterly_roi
from main_marts.sum_quarterly_campaign_totals
