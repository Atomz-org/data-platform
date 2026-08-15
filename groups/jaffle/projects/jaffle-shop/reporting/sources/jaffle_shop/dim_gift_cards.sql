-- source extract for dim_gift_cards (PII columns excluded by the MDL projection)
select gift_card_id, card_number, customer_id, gift_card_status, initial_balance, latest_balance, total_redeemed, issued_date, expires_date, last_redemption_date, is_expired, is_fully_redeemed
from main_marts.dim_gift_cards
