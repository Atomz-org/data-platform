-- source extract for met_monthly_waste_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    location_id,
    waste_to_revenue_pct,
    mom_waste_cost_change
from main_marts.met_monthly_waste_metrics
