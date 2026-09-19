-- source extract for int_invoice_payment_matching (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    invoice_id,
    payment_match_status
from main_marts.int_invoice_payment_matching
