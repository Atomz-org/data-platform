-- source extract for dist_campaign_roi (PII columns excluded by the MDL projection)
select utilization_bucket, campaign_count, avg_utilization, mean_utilization, median_utilization, total_campaigns
from main_marts.dist_campaign_roi
