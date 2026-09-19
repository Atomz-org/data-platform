-- source extract for int_weekly_orders_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    week_start,
    location_id,
    order_count,
    total_revenue,
    active_days_in_week
from main_marts.int_weekly_orders_by_store
