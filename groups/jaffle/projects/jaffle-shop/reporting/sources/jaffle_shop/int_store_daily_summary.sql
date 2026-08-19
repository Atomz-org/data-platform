-- source extract for int_store_daily_summary (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    order_date,
    order_count,
    daily_revenue,
    labor_hours,
    revenue_per_labor_hour,
    waste_cost,
    waste_as_pct_of_revenue
from main_marts.int_store_daily_summary
