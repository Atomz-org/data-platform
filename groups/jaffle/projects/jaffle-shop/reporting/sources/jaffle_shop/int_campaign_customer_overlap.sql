-- source extract for int_campaign_customer_overlap (PII columns excluded by the MDL projection)
select campaigns_targeted, customer_count, overlap_tier
from main_marts.int_campaign_customer_overlap
