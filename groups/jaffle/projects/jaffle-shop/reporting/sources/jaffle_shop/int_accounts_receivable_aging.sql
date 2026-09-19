-- source extract for int_accounts_receivable_aging (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    receivable_id,
    customer_id,
    amount_outstanding,
    days_past_due,
    aging_bucket,
    aging_bucket_sort
from main_marts.int_accounts_receivable_aging
