-- source extract for int_receipt_quality_check (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    purchase_order_id,
    quality_pass_rate_pct
from main_marts.int_receipt_quality_check
