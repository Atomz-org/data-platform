-- source extract for int_payment_method_mix (PII columns excluded by the MDL projection)
select order_id, payment_method, transaction_count, method_total, completed_amount, failed_amount, first_payment_date, last_payment_date
from main_marts.int_payment_method_mix
