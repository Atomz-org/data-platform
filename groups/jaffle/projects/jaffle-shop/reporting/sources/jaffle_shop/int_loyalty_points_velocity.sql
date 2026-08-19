-- source extract for int_loyalty_points_velocity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    points_month,
    points_earned,
    points_redeemed,
    rolling_3m_avg_earned
from main_marts.int_loyalty_points_velocity
