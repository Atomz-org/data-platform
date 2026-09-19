-- source extract for int_store_metrics_weekly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    week_start,
    location_id,
    location_name,
    order_count,
    unique_customers,
    total_revenue,
    avg_ticket_size
from main_marts.int_store_metrics_weekly
