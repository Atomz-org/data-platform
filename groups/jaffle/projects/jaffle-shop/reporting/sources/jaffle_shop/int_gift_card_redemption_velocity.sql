-- source extract for int_gift_card_redemption_velocity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    gift_card_id,
    total_transactions,
    total_redeemed,
    avg_transaction_amount,
    first_use_date,
    last_use_date,
    active_span_days,
    avg_days_between_uses,
    transactions_per_day
from main_marts.int_gift_card_redemption_velocity
