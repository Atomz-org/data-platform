-- source extract for inc_fct_inventory_movements (PII columns excluded by the MDL projection)
select movement_id, product_id, location_id, movement_type, quantity, moved_at, movement_month
from main_marts.inc_fct_inventory_movements
