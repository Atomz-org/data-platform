-- source extract for int_store_inventory_cost (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    total_inventory_value,
    estimated_monthly_holding_cost
from main_marts.int_store_inventory_cost
