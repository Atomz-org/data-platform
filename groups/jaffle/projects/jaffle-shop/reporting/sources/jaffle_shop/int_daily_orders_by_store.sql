-- source extract for int_daily_orders_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_date,
    location_id,
    location_name,
    order_count,
    unique_customers,
    total_revenue,
    avg_order_value
from main_marts.int_daily_orders_by_store
