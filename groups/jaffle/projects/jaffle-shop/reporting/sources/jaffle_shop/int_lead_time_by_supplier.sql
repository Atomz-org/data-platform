-- source extract for int_lead_time_by_supplier (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    count_completed_orders,
    avg_lead_time_days,
    avg_lead_time_variance_days,
    on_time_delivery_rate
from main_marts.int_lead_time_by_supplier
