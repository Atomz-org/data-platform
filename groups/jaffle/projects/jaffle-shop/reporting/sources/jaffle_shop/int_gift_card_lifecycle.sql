-- source extract for int_gift_card_lifecycle (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    gift_card_id,
    card_age_days,
    utilization_pct,
    balance_tier
from main_marts.int_gift_card_lifecycle
