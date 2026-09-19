-- source extract for fnl_order_conversion (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_month,
    total_orders_placed,
    orders_with_revenue,
    revenue_capture_rate_pct,
    fulfillment_rate_pct
from main_marts.fnl_order_conversion
