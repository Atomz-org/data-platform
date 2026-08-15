-- source extract for int_inventory_movement_enriched (PII columns excluded by the MDL projection)
select movement_id, product_name, location_name, inbound_quantity, outbound_quantity, product_id, product_type, location_id, movement_type, reference_type, reference_id, quantity, absolute_quantity, moved_at
from main_marts.int_inventory_movement_enriched
