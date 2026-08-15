-- source extract for int_gift_card_running_balance (PII columns excluded by the MDL projection)
select gift_card_id, card_number, initial_balance, processed_date, daily_redemption_amount, running_balance_after, customer_id, gift_card_status, issued_date, expires_date, daily_transaction_count
from main_marts.int_gift_card_running_balance
