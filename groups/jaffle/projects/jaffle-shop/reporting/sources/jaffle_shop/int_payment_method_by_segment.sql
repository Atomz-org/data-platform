-- source extract for int_payment_method_by_segment (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    rfm_segment,
    payment_method,
    pct_of_segment_transactions
from main_marts.int_payment_method_by_segment
