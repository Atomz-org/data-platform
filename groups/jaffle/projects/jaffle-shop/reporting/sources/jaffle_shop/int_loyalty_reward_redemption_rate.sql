-- source extract for int_loyalty_reward_redemption_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    redemption_rate_pct,
    redemption_behavior
from main_marts.int_loyalty_reward_redemption_rate
