-- source extract for rank_campaigns_by_roi (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, total_spend, budget, budget_utilization, roi_rank, roi_quartile
from main_marts.rank_campaigns_by_roi
