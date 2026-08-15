-- source extract for rpt_gift_card_velocity (PII columns excluded by the MDL projection)
select report_month, cards_issued, total_issued_value, avg_issued_value, cards_first_used, total_redeemed_amount, avg_txn_amount, avg_days_between_uses, avg_transactions_per_card, avg_active_span_days, net_liability_change, activation_rate
from main_marts.rpt_gift_card_velocity
