-- source extract for int_payment_method_mix (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_id,
    payment_method,
    transaction_count,
    method_total,
    completed_amount,
    failed_amount
from main_marts.int_payment_method_mix
