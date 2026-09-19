-- source extract for int_loyalty_points_balance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    current_points_balance,
    total_points_earned,
    total_points_redeemed
from main_marts.int_loyalty_points_balance
