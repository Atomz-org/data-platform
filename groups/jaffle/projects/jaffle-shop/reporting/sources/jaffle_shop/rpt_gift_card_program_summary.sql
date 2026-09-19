-- source extract for rpt_gift_card_program_summary (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    total_cards,
    overall_redemption_rate_pct,
    breakage_value
from main_marts.rpt_gift_card_program_summary
