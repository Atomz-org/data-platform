-- source extract for int_gift_card_running_balance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    gift_card_id,
    card_number,
    initial_balance,
    processed_date,
    daily_redemption_amount,
    running_balance_after
from main_marts.int_gift_card_running_balance
