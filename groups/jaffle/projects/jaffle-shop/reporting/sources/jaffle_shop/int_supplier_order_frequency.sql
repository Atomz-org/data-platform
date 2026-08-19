-- source extract for int_supplier_order_frequency (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    avg_days_between_orders,
    total_order_value
from main_marts.int_supplier_order_frequency
