-- source extract for int_accounts_receivable_turnover (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    sales_month,
    ar_turnover_ratio,
    days_sales_outstanding
from main_marts.int_accounts_receivable_turnover
