-- source extract for int_gift_card_balance_monthly (PII columns excluded by the MDL projection)
select month_start, gift_card_id, customer_id, end_of_month_balance, total_redeemed_to_date, card_number, gift_card_status, initial_balance
from main_marts.int_gift_card_balance_monthly
