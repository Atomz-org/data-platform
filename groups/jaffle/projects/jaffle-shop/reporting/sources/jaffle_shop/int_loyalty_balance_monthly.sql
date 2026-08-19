-- source extract for int_loyalty_balance_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    loyalty_member_id,
    customer_id,
    end_of_month_balance,
    points_earned_in_month,
    points_redeemed_in_month,
    transactions_in_month
from main_marts.int_loyalty_balance_monthly
