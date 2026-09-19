-- source extract for met_daily_revenue_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    revenue_date,
    location_id,
    store_name,
    total_revenue,
    revenue_7d_avg,
    revenue_28d_avg
from main_marts.met_daily_revenue_by_store
