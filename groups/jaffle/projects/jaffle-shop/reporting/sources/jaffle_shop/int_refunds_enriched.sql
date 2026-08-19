-- source extract for int_refunds_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    refund_id,
    refund_amount,
    refund_pct_of_invoice,
    days_to_resolution
from main_marts.int_refunds_enriched
