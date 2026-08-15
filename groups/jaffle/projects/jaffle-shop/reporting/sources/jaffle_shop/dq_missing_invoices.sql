-- source extract for dq_missing_invoices (PII columns excluded by the MDL projection)
select order_id, order_status, missing_invoice_type, customer_id, location_id, ordered_at, order_total, 'completed'
from main_marts.dq_missing_invoices
