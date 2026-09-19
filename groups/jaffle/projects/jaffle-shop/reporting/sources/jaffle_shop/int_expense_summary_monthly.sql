-- source extract for int_expense_summary_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    expense_category_id,
    category_name,
    expense_month,
    expense_count,
    total_expense_amount,
    avg_expense_amount
from main_marts.int_expense_summary_monthly
