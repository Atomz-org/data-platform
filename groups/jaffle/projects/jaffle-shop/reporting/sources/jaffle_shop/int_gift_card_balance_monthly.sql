-- source extract for int_gift_card_balance_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    gift_card_id,
    customer_id,
    end_of_month_balance,
    total_redeemed_to_date
from main_marts.int_gift_card_balance_monthly
