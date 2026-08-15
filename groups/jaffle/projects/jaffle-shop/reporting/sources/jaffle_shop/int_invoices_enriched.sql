-- source extract for int_invoices_enriched (PII columns excluded by the MDL projection)
select invoice_id, order_id, customer_id, customer_name, location_id, total_amount, days_to_payment, days_overdue, invoice_status, subtotal, tax_amount, amount_paid, amount_due, order_subtotal, order_tax_paid, order_total, issued_date, due_date, paid_date, order_date
from main_marts.int_invoices_enriched
