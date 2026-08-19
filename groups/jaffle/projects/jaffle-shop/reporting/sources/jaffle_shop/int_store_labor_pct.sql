-- source extract for int_store_labor_pct (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    report_month,
    labor_cost_pct,
    fleet_avg_labor_pct
from main_marts.int_store_labor_pct
