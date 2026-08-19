-- source extract for dq_missing_invoices (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_id,
    order_status,
    missing_invoice_type
from main_marts.dq_missing_invoices
