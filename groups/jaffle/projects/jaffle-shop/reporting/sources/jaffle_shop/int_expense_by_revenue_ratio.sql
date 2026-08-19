-- source extract for int_expense_by_revenue_ratio (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    expense_month,
    expense_to_revenue_pct
from main_marts.int_expense_by_revenue_ratio
