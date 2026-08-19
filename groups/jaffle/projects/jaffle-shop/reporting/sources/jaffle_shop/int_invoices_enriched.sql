-- source extract for int_invoices_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    invoice_id,
    order_id,
    customer_id,
    customer_name,
    location_id,
    total_amount,
    days_to_payment,
    days_overdue
from main_marts.int_invoices_enriched
