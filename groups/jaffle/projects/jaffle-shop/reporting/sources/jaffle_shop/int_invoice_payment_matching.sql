-- source extract for int_invoice_payment_matching (PII columns excluded by the MDL projection)
select invoice_id, payment_match_status, order_id, invoice_amount, total_paid, payment_count, payment_variance
from main_marts.int_invoice_payment_matching
