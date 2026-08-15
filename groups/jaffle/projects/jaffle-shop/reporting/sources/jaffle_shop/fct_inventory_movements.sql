-- source extract for fct_inventory_movements (PII columns excluded by the MDL projection)
select movement_id, product_id, product_name, product_type, location_id, location_name, movement_type, reference_type, reference_id, quantity, absolute_quantity, is_inbound, is_outbound, moved_at
from main_marts.fct_inventory_movements
