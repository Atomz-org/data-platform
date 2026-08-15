-- source extract for inc_fct_invoices (PII columns excluded by the MDL projection)
select invoice_id, customer_id, order_id, issued_date, due_date, total_amount, tax_amount, invoice_status, invoice_month, invoice_status_derived
from main_marts.inc_fct_invoices
