-- source extract for int_revenue_by_daypart (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    revenue_date,
    location_id,
    daypart,
    order_count,
    total_revenue,
    avg_order_value
from main_marts.int_revenue_by_daypart
