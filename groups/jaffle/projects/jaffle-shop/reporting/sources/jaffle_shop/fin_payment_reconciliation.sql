-- source extract for fin_payment_reconciliation (PII columns excluded by the MDL projection)
select payment_transaction_id, order_id, payment_amount, payment_status, payment_method, processed_date, invoice_id, total_amount, invoice_status, reconciliation_status, variance_amount
from main_marts.fin_payment_reconciliation
