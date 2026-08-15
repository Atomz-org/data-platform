-- source extract for int_gift_card_lifecycle (PII columns excluded by the MDL projection)
select gift_card_id, card_age_days, utilization_pct, balance_tier, customer_id, gift_card_status, initial_balance, current_balance, issued_date, expires_date, usage_count, total_spent, amount_used
from main_marts.int_gift_card_lifecycle
