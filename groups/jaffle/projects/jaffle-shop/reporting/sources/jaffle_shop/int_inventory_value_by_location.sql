-- source extract for int_inventory_value_by_location (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    location_id,
    current_quantity,
    unit_cost,
    inventory_value,
    last_movement_at
from main_marts.int_inventory_value_by_location
