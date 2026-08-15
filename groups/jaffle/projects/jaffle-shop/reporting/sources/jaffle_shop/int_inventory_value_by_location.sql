-- source extract for int_inventory_value_by_location (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, unit_cost, inventory_value, last_movement_at
from main_marts.int_inventory_value_by_location
