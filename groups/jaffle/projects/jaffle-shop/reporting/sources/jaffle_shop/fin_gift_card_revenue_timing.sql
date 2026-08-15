-- source extract for fin_gift_card_revenue_timing (PII columns excluded by the MDL projection)
select issue_month, cards_issued, total_initial_value, total_redeemed_value, total_remaining_balance, avg_days_to_use, used_within_7_days, used_within_30_days, used_within_90_days, never_used, never_used_pct, redemption_rate_pct
from main_marts.fin_gift_card_revenue_timing
