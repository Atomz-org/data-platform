-- source extract for rpt_gift_card_liability (PII columns excluded by the MDL projection)
select gift_card_status, is_expired, is_fully_redeemed, card_count, total_initial_balance, total_redeemed, total_outstanding_balance, avg_outstanding_balance, active_liability, total_active_liability, grand_total_outstanding
from main_marts.rpt_gift_card_liability
