-- source extract for rpt_gift_card_program_summary (PII columns excluded by the MDL projection)
select total_cards, overall_redemption_rate_pct, breakage_value, active_cards, fully_redeemed_cards, expired_cards, total_issued_value, total_outstanding_balance, total_redeemed_value
from main_marts.rpt_gift_card_program_summary
