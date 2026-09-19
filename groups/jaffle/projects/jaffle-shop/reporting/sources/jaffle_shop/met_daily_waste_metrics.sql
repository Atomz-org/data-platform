-- source extract for met_daily_waste_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    waste_date,
    location_id,
    total_waste_cost
from main_marts.met_daily_waste_metrics
