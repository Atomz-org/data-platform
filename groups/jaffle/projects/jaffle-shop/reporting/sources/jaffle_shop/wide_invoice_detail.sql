-- source extract for wide_invoice_detail (PII columns excluded by the MDL projection)
select invoice_id, customer_id, customer_name, location_id, location_name, issued_date, due_date, total_amount, tax_amount, invoice_status, line_item_count, total_paid, payment_count, last_payment_date, outstanding_balance
from main_marts.wide_invoice_detail
