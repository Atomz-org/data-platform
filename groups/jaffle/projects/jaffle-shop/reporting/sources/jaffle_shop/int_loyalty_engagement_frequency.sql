-- source extract for int_loyalty_engagement_frequency (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    avg_days_between_transactions,
    engagement_tier
from main_marts.int_loyalty_engagement_frequency
