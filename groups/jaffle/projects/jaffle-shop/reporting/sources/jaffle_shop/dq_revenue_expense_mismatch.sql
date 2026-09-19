-- source extract for dq_revenue_expense_mismatch (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    check_date,
    expense_to_revenue_ratio,
    anomaly_type
from main_marts.dq_revenue_expense_mismatch
