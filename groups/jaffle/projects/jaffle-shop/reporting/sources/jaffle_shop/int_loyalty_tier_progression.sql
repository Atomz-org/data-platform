-- source extract for int_loyalty_tier_progression (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    customer_id,
    current_tier_name,
    earned_tier_name,
    points_to_next_tier
from main_marts.int_loyalty_tier_progression
