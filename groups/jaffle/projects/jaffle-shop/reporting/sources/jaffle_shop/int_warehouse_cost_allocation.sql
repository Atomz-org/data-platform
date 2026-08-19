-- source extract for int_warehouse_cost_allocation (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    warehouse_id,
    capacity_utilization_pct,
    total_inventory_value
from main_marts.int_warehouse_cost_allocation
