-- source extract for stg_derived_invoice_with_customer (PII columns excluded by the MDL projection)
select invoice_id, customer_id, customer_name, issued_date, due_date, total_amount, invoice_status
from main_marts.stg_derived_invoice_with_customer
