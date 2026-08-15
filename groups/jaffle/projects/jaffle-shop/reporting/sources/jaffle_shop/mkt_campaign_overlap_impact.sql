-- source extract for mkt_campaign_overlap_impact (PII columns excluded by the MDL projection)
select campaign_a, campaign_a_name, campaign_b, campaign_b_name, overlap_start, overlap_end, overlap_days, campaign_a_roi, campaign_b_roi, campaign_a_revenue, campaign_b_revenue, overlap_severity
from main_marts.mkt_campaign_overlap_impact
