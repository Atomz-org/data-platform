-- source extract for int_inventory_current_level (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, total_inbound, total_outbound, last_movement_at, total_movements
from main_marts.int_inventory_current_level
