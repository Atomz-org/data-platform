-- source extract for int_budget_utilization_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    budget_id,
    utilization_rate_pct,
    budget_status
from main_marts.int_budget_utilization_rate
