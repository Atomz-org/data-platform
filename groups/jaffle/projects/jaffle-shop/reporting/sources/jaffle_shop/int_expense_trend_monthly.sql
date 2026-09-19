-- source extract for int_expense_trend_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    expense_category_id,
    category_name,
    expense_month,
    total_expense_amount,
    mom_change_amount,
    mom_change_pct,
    rolling_3m_avg_expense
from main_marts.int_expense_trend_monthly
