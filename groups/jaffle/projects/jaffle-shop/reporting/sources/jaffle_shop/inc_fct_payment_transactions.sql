-- source extract for inc_fct_payment_transactions (PII columns excluded by the MDL projection)
select payment_transaction_id, order_id, gift_card_id, payment_method, payment_status, reference_number, payment_amount, processed_date, payment_month
from main_marts.inc_fct_payment_transactions
