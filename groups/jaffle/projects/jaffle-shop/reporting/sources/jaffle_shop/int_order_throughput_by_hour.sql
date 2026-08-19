-- source extract for int_order_throughput_by_hour (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    order_hour,
    avg_orders_per_hour,
    hour_share_of_total_pct
from main_marts.int_order_throughput_by_hour
