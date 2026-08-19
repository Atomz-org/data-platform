-- source extract for int_delivery_on_time_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    total_deliveries,
    on_time_deliveries,
    late_deliveries,
    on_time_rate,
    avg_transit_days
from main_marts.int_delivery_on_time_rate
