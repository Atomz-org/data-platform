-- source extract for int_budget_vs_actual (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    budget_id,
    location_id,
    budget_type,
    budget_month,
    budgeted_amount,
    actual_amount,
    variance_amount,
    variance_pct
from main_marts.int_budget_vs_actual
