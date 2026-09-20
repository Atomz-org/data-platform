-- source extract for int_campaign_customer_overlap (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaigns_targeted,
    customer_count,
    overlap_tier
from main_marts.int_campaign_customer_overlap
