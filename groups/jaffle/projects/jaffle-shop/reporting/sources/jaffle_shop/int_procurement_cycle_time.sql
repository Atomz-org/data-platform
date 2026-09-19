-- source extract for int_procurement_cycle_time (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    purchase_order_id,
    supplier_id,
    cycle_time_days,
    expected_cycle_time_days,
    cycle_time_variance_days
from main_marts.int_procurement_cycle_time
