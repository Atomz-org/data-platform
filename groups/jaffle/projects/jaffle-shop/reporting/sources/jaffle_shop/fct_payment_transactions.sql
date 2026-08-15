-- source extract for fct_payment_transactions (PII columns excluded by the MDL projection)
select payment_transaction_id, order_id, gift_card_id, payment_method, payment_status, reference_number, payment_amount, processed_date, location_id, customer_id, order_total, order_date, is_completed, is_gift_card_payment
from main_marts.fct_payment_transactions
