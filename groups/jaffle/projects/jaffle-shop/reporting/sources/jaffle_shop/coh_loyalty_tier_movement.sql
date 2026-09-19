-- source extract for coh_loyalty_tier_movement (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    activity_month,
    tier_name,
    member_count,
    maintained_count
from main_marts.coh_loyalty_tier_movement
