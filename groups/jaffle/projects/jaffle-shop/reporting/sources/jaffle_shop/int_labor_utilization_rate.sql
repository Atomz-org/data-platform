-- source extract for int_labor_utilization_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    work_date,
    orders_per_labor_hour,
    utilization_tier
from main_marts.int_labor_utilization_rate
