-- source extract for met_daily_labor_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    work_date,
    location_id,
    orders_per_labor_hour,
    labor_cost_pct_of_revenue
from main_marts.met_daily_labor_metrics
