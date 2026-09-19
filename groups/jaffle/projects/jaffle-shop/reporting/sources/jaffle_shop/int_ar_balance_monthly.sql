-- source extract for int_ar_balance_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    open_receivables,
    total_outstanding,
    outstanding_current,
    outstanding_90_plus
from main_marts.int_ar_balance_monthly
