-- source extract for met_daily_inventory_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    movement_date,
    location_id,
    total_movements
from main_marts.met_daily_inventory_metrics
