-- source extract for fct_invoices (PII columns excluded by the MDL projection)
select invoice_id, order_id, customer_id, customer_name, location_id, invoice_status, subtotal, tax_amount, total_amount, amount_paid, amount_due, order_subtotal, order_tax_paid, order_total, issued_date, due_date, paid_date, order_date, days_to_payment, days_overdue, is_paid, is_overdue
from main_marts.fct_invoices
