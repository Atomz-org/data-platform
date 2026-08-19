-- source extract for int_monthly_orders_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    location_id,
    order_count,
    total_revenue,
    mom_revenue_growth,
    yoy_revenue_growth
from main_marts.int_monthly_orders_by_store
